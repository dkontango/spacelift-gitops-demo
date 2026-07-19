# Build a small static binary, ship it on a minimal base.
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/contact-service .

FROM alpine:3.20
# ca-certificates: needed for TLS to Bao (HTTPS) and STARTTLS to the SMTP relay.
RUN apk add --no-cache ca-certificates && adduser -D -u 10001 app
USER app
COPY --from=build /out/contact-service /usr/local/bin/contact-service
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/contact-service"]
