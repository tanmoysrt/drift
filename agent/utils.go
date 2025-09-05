package main

import (
	"fmt"
	"net"
)

func findAvailablePort() (uint16, error) {
	ln, err := net.Listen("tcp", ":0")
	if err != nil {
		return 0, fmt.Errorf("failed to find available port: %w", err)
	}
	defer ln.Close()

	addr := ln.Addr().(*net.TCPAddr)
	return uint16(addr.Port), nil
}

func (agent *DriftAgent) BrowserProxyPort() uint16 {
	if agent.IsHttps {
		return 8443
	}
	return 8080
}

func (agent *DriftAgent) GenerateBrowserSessionEndpoint(sessionId string) string {
	scheme := "http"
	if agent.IsHttps {
		scheme = "https"
	}
	return fmt.Sprintf("%s://%s:%d/%s", scheme, agent.Domain, agent.BrowserProxyPort(), sessionId)
}
