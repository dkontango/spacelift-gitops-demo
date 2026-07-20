// Contact-service: a tiny HTTP endpoint behind the guide's "Contact Us" form.
//
// It validates a submitted email (format + MX lookup), then sends a real
// thank-you confirmation to that address via the Purelymail SMTP relay. SMTP
// credentials are read from OpenBao at startup — never shipped to the browser.
//
// One endpoint: POST /contact  {"email": "...", "name": "...", "message": "..."}
// Plus GET /healthz for liveness.
//
// Config (env):
//
//	LISTEN_ADDR        default ":8080"
//	ALLOWED_ORIGIN     CORS origin allowed to POST (e.g. https://dkontango.github.io)
//	FROM_ADDR          envelope/from address (must be a Purelymail domain, e.g. no-reply@kontango.io)
//	FROM_NAME          display name for the From header
//	BAO_ADDR           OpenBao address (e.g. https://secrets.kontango.net)
//	BAO_NAMESPACE      OpenBao namespace (e.g. kontango)
//	BAO_TOKEN          token, OR BAO_TOKEN_FILE pointing at /run/bao-token
//	BAO_TOKEN_FILE     path to a file holding the token (schmutz agent style)
//	SMTP_SECRET_PATH   KV v2 data path, default "secret/data/shared/purelymail"
package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/smtp"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

func base64Std(s string) string { return base64.StdEncoding.EncodeToString([]byte(s)) }

// RFC 5322-ish practical email regex: good enough to reject garbage without
// rejecting valid addresses. Deliverability is checked separately via MX.
var emailRe = regexp.MustCompile(`^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$`)

type smtpCreds struct {
	Host string
	Port string
	User string
	Pass string
}

type server struct {
	creds     smtpCreds
	fromAddr  string
	fromName  string
	adminAddr string // gets a separate "new submission" copy; empty disables it
	allowed   string
	limiter   *rateLimiter
}

type contactReq struct {
	Email   string `json:"email"`
	Name    string `json:"name"`
	Message string `json:"message"`
	Website string `json:"website"` // honeypot: real users leave this blank
}

func main() {
	listen := env("LISTEN_ADDR", ":8080")
	s := &server{
		fromAddr:  env("FROM_ADDR", "no-reply@kontango.io"),
		fromName:  env("FROM_NAME", "Kontango — Spacelift GitOps Demo"),
		adminAddr: env("ADMIN_ADDR", "admin@kontango.us"),
		allowed:   env("ALLOWED_ORIGIN", "*"),
		limiter:   newRateLimiter(5, time.Minute), // 5 submits/min/IP
	}

	creds, err := loadSMTPFromBao()
	if err != nil {
		log.Fatalf("failed to load SMTP creds from Bao: %v", err)
	}
	s.creds = creds
	log.Printf("SMTP relay %s:%s as %s; from=%s; admin=%s; origin=%s",
		creds.Host, creds.Port, creds.User, s.fromAddr, adminOrNone(s.adminAddr), s.allowed)

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/contact", s.handleContact)

	srv := &http.Server{
		Addr:              listen,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      30 * time.Second,
	}
	log.Printf("contact-service listening on %s", listen)
	log.Fatal(srv.ListenAndServe())
}

func (s *server) cors(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", s.allowed)
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	w.Header().Set("Vary", "Origin")
}

func (s *server) handleContact(w http.ResponseWriter, r *http.Request) {
	s.cors(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}
	if !s.limiter.allow(clientIP(r)) {
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "too many requests, try again shortly"})
		return
	}

	var req contactReq
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024)).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}
	// honeypot: if the hidden field is filled, silently accept (don't tip off bots)
	if strings.TrimSpace(req.Website) != "" {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}

	email := strings.TrimSpace(req.Email)
	if err := validateEmail(email); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	name := sanitizeHeader(strings.TrimSpace(req.Name))
	if name == "" {
		name = "there"
	}

	if err := s.sendThankYou(email, name); err != nil {
		log.Printf("send failed to %s: %v", email, err)
		writeJSON(w, http.StatusBadGateway, map[string]string{"error": "could not send confirmation email; please try again later"})
		return
	}
	log.Printf("thank-you sent to %s", email)

	// Best-effort admin notification: a separate email so the submitter never
	// sees the admin address. A failure here doesn't fail the user's request —
	// they already got their confirmation.
	if s.adminAddr != "" {
		if err := s.sendAdminNotice(email, name, req.Message); err != nil {
			log.Printf("admin notice to %s failed: %v", s.adminAddr, err)
		} else {
			log.Printf("admin notice sent to %s", s.adminAddr)
		}
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"status":  "sent",
		"message": "Thanks — a confirmation email is on its way to " + email + ".",
	})
}

// validateEmail: format check + a DNS MX (fallback A) lookup on the domain so we
// only accept addresses at a domain that can actually receive mail.
func validateEmail(email string) error {
	if email == "" {
		return errors.New("email is required")
	}
	if len(email) > 254 || !emailRe.MatchString(email) {
		return errors.New("that doesn't look like a valid email address")
	}
	at := strings.LastIndex(email, "@")
	domain := email[at+1:]
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()
	var r net.Resolver
	if mx, err := r.LookupMX(ctx, domain); err == nil && len(mx) > 0 {
		return nil
	}
	// some domains accept mail with only an A/AAAA record (implicit MX)
	if ips, err := r.LookupIPAddr(ctx, domain); err == nil && len(ips) > 0 {
		return nil
	}
	return errors.New("the email domain can't receive mail (no MX record found)")
}

func (s *server) sendThankYou(to, name string) error {
	return s.sendMail(to, "Thanks for reaching out — Spacelift GitOps Demo", thankYouBody(name), "")
}

// sendAdminNotice emails admin a separate "new submission" copy including the
// submitter's name, address, and message. Reply-To is set to the submitter so
// admin can reply directly. The submitter never sees the admin address.
func (s *server) sendAdminNotice(submitterEmail, submitterName, message string) error {
	if message == "" {
		message = "(no message provided)"
	}
	body := strings.Join([]string{
		"New contact submission from the Spacelift GitOps demo site.",
		"",
		"Name:    " + submitterName,
		"Email:   " + submitterEmail,
		"",
		"Message:",
		message,
	}, "\r\n")
	return s.sendMail(s.adminAddr, "New contact submission — "+submitterEmail, body, submitterEmail)
}

// sendMail builds a UTF-8 text email and relays it. replyTo, if set, becomes the
// Reply-To header (used so admin can reply straight to the submitter).
func (s *server) sendMail(to, subject, body, replyTo string) error {
	from := fmt.Sprintf("%s <%s>", mimeEncode(s.fromName), s.fromAddr)
	var msg bytes.Buffer
	fmt.Fprintf(&msg, "From: %s\r\n", from)
	fmt.Fprintf(&msg, "To: %s\r\n", to)
	if replyTo != "" {
		fmt.Fprintf(&msg, "Reply-To: %s\r\n", replyTo)
	}
	fmt.Fprintf(&msg, "Subject: %s\r\n", mimeEncode(subject))
	fmt.Fprintf(&msg, "MIME-Version: 1.0\r\n")
	fmt.Fprintf(&msg, "Content-Type: text/plain; charset=\"utf-8\"\r\n")
	fmt.Fprintf(&msg, "Date: %s\r\n", time.Now().Format(time.RFC1123Z))
	fmt.Fprintf(&msg, "\r\n%s\r\n", body)

	addr := s.creds.Host + ":" + s.creds.Port
	auth := smtp.PlainAuth("", s.creds.User, s.creds.Pass, s.creds.Host)
	// net/smtp.SendMail negotiates STARTTLS on :587 automatically when the
	// server advertises it (Purelymail does).
	return smtp.SendMail(addr, auth, s.fromAddr, []string{to}, msg.Bytes())
}

func adminOrNone(a string) string {
	if a == "" {
		return "(disabled)"
	}
	return a
}

func thankYouBody(name string) string {
	return strings.Join([]string{
		"Hi " + name + ",",
		"",
		"Thanks for reaching out about the Spacelift GitOps demo. This note confirms",
		"we received your message — a real email, sent by a small Go service that",
		"validates your address and relays through our own SMTP, exactly the kind of",
		"end-to-end, policy-gated workflow the demo is about.",
		"",
		"We'll follow up shortly. In the meantime, the full onboarding guide and the",
		"17-step walkthrough live at the site you came from.",
		"",
		"— The Kontango team",
		"",
		"(You received this because someone entered this address in the contact form",
		"on the Spacelift GitOps demo site. If that wasn't you, you can ignore it.)",
	}, "\r\n")
}

// ---- helpers ----

func loadSMTPFromBao() (smtpCreds, error) {
	baoAddr := env("BAO_ADDR", "https://secrets.kontango.net")
	ns := env("BAO_NAMESPACE", "kontango")
	path := env("SMTP_SECRET_PATH", "secret/data/shared/purelymail")

	token := os.Getenv("BAO_TOKEN")
	if token == "" {
		if f := os.Getenv("BAO_TOKEN_FILE"); f != "" {
			b, err := os.ReadFile(f)
			if err != nil {
				return smtpCreds{}, fmt.Errorf("read BAO_TOKEN_FILE: %w", err)
			}
			token = strings.TrimSpace(string(b))
		}
	}
	if token == "" {
		return smtpCreds{}, errors.New("no BAO_TOKEN or BAO_TOKEN_FILE set")
	}

	url := strings.TrimRight(baoAddr, "/") + "/v1/" + path
	req, _ := http.NewRequest(http.MethodGet, url, nil)
	req.Header.Set("X-Vault-Token", token)
	if ns != "" {
		req.Header.Set("X-Vault-Namespace", ns)
	}
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return smtpCreds{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return smtpCreds{}, fmt.Errorf("bao returned %d for %s", resp.StatusCode, path)
	}
	var out struct {
		Data struct {
			Data map[string]string `json:"data"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return smtpCreds{}, err
	}
	d := out.Data.Data
	c := smtpCreds{
		Host: d["smtp_host"],
		Port: d["smtp_port"],
		User: d["smtp_user"],
		Pass: d["smtp_password"],
	}
	if c.Host == "" || c.Port == "" || c.User == "" || c.Pass == "" {
		return smtpCreds{}, errors.New("purelymail secret missing smtp_host/port/user/password")
	}
	return c, nil
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func clientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		return strings.TrimSpace(strings.Split(xff, ",")[0])
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// sanitizeHeader strips CR/LF to prevent header injection via the name field.
func sanitizeHeader(s string) string {
	s = strings.ReplaceAll(s, "\r", "")
	s = strings.ReplaceAll(s, "\n", "")
	if len(s) > 120 {
		s = s[:120]
	}
	return s
}

// mimeEncode RFC 2047-encodes a header value if it contains non-ASCII.
func mimeEncode(s string) string {
	for _, r := range s {
		if r > 127 {
			return "=?utf-8?B?" + base64Std(s) + "?="
		}
	}
	return s
}

// ---- tiny rate limiter (token-bucket per IP) ----

type rateLimiter struct {
	mu     sync.Mutex
	hits   map[string][]time.Time
	max    int
	window time.Duration
}

func newRateLimiter(max int, window time.Duration) *rateLimiter {
	return &rateLimiter{hits: map[string][]time.Time{}, max: max, window: window}
}

func (l *rateLimiter) allow(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := time.Now()
	cutoff := now.Add(-l.window)
	kept := l.hits[key][:0]
	for _, t := range l.hits[key] {
		if t.After(cutoff) {
			kept = append(kept, t)
		}
	}
	if len(kept) >= l.max {
		l.hits[key] = kept
		return false
	}
	l.hits[key] = append(kept, now)
	return true
}
