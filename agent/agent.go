package main

import (
	"crypto/tls"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"syscall"

	"github.com/labstack/echo/v4"
	"golang.org/x/crypto/acme/autocert"
)

type DriftAgent struct {
	Headless bool

	AuthToken string
	Domain    string
	IsHttps   bool

	UserDataDirectory  string
	RecordingDirectory string

	Sessions           map[string]*BrowserSession
	echoHandler        *echo.Echo
	apiServer          *http.Server
	browserProxyServer *http.Server
	challengeServer    *http.Server
	autoCertManager    *autocert.Manager
	tlsConfig          *tls.Config
	Mutex              *sync.RWMutex
}

type DraftAgentOptions struct {
	Headless          bool   `json:"headless"`
	Domain            string `json:"domain"`
	IsHttps           bool   `json:"is_https"`
	AuthToken         string `json:"auth_token"`
	BaseDataDirectory string `json:"base_data_directory"`
	LetsEncryptEmail  string `json:"lets_encrypt_email"`
}

func NewDriftAgent(options DraftAgentOptions) *DriftAgent {
	var tlsConfig *tls.Config
	var autoCertManager *autocert.Manager

	if options.IsHttps {
		autoCertManager = &autocert.Manager{
			Cache:      autocert.DirCache(filepath.Join(options.BaseDataDirectory, "certs")),
			Prompt:     autocert.AcceptTOS,
			HostPolicy: autocert.HostWhitelist(options.Domain),
			Email:      options.LetsEncryptEmail,
		}

		// Shared TLS config
		tlsConfig = &tls.Config{
			GetCertificate: autoCertManager.GetCertificate,
		}
	}

	return &DriftAgent{
		Mutex:              &sync.RWMutex{},
		Headless:           options.Headless,
		Domain:             options.Domain,
		IsHttps:            options.IsHttps,
		AuthToken:          options.AuthToken,
		Sessions:           make(map[string]*BrowserSession),
		UserDataDirectory:  filepath.Join(options.BaseDataDirectory, "user_data"),
		RecordingDirectory: filepath.Join(options.BaseDataDirectory, "recordings"),
		echoHandler:        nil,
		browserProxyServer: nil,
		challengeServer:    nil,
		autoCertManager:    autoCertManager,
		tlsConfig:          tlsConfig,
	}
}

func (agent *DriftAgent) Start() {
	agent.CleanupUserDataDirectories()
	agent.StartAPIServer()
	agent.StartACMEChallengeServer()
	agent.StartBrowserProxy()
}

func (agent *DriftAgent) Stop() {
	agent.StopAPIServer()
	agent.StopACMEChallengeServer()
	agent.TerminateAllBrowserSessions()
	agent.StopBrowserProxy()
}

func (agent *DriftAgent) WaitForGracefulShutdown() {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	<-sigCh
	fmt.Println("\nReceived shutdown signal. Cleaning up...")
	agent.Stop()
}
