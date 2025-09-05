# Ref : https://github.com/playwright-community/playwright-go/blob/c6ac7e7eef729eb8fbfb88564cb06a6c316e4d64/Dockerfile.example

# Stage 1: Modules caching
FROM golang:1.24 AS modules
COPY go.mod go.sum /modules/
WORKDIR /modules
RUN go mod download

# Stage 2: Build
FROM golang:1.24 AS builder
ARG TARGETOS
ARG TARGETARCH
COPY --from=modules /go/pkg /go/pkg
COPY . /workdir
WORKDIR /workdir
# Install playwright CLI with right version for later use
RUN PWGO_VER=$(grep -oE "playwright-go v\\S+" /workdir/go.mod | sed 's/playwright-go //g') \
    && go install github.com/playwright-community/playwright-go/cmd/playwright@${PWGO_VER}
# Build your Go app for the target platform
RUN GOOS=$TARGETOS GOARCH=$TARGETARCH go build -o /bin/drift-agent

# Stage 3: Build Final image
FROM ubuntu:noble
COPY --from=builder /go/bin/playwright /bin/drift-agent /
RUN apt-get update && apt-get install -y \
      ca-certificates \
      tzdata \
      ffmpeg \
    # Install only Chromium + ffmpeg module
    && /playwright install --with-deps chromium ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Add entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/data"]
ENTRYPOINT ["/entrypoint.sh"]
