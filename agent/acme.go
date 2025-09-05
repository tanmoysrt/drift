package main

import (
	"log"
	"net/http"
)

func (agent *DriftAgent) StartACMEChallengeServer() {
	if !agent.IsHttps {
		return
	}
	challengeSrv := &http.Server{
		Addr:    ":80",
		Handler: agent.autoCertManager.HTTPHandler(nil),
	}

	agent.challengeServer = challengeSrv
	go func() {
		log.Printf("Starting HTTP challenge listener on %s", challengeSrv.Addr)
		if err := challengeSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("http challenge server stopped: %v", err)
		}
	}()
}

func (agent *DriftAgent) StopACMEChallengeServer() {
	if agent.challengeServer != nil {
		_ = agent.challengeServer.Close()
	}
}
