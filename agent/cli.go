package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/playwright-community/playwright-go"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.Flags().SortFlags = false
	rootCmd.AddCommand(setupCmd)
	rootCmd.AddCommand(runCmd)
	runCmd.Flags().String("config", "", "Path to configuration file")
}

var setupCmd = &cobra.Command{
	Use:   "setup",
	Short: "Setup command sets up the environment for running UI tests.",
	Long:  `Setup command sets up the environment for running UI tests.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Setup playwright with chromium
		playwright.Install(&playwright.RunOptions{
			Browsers: []string{"chromium"},
		})

		// Verify installation
		pw, err := playwright.Run()
		if err != nil {
			panic(err)
		}
		browser, err := pw.Chromium.Launch()
		if err != nil {
			panic(err)
		}
		browserPath := pw.Chromium.ExecutablePath()
		fmt.Println("Chromium browser path:", browserPath)
		browser.Close()
		pw.Stop()
	},
}

var runCmd = &cobra.Command{
	Use:   "run",
	Short: "Run Drift agent.",
	Long:  `Run Drift agent.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Read config file path
		configFilePath, _ := cmd.Flags().GetString("config")
		if configFilePath == "" {
			fmt.Println("Please provide a config file path using --config flag.")
			return
		}

		// Load configuration from file
		data, err := os.ReadFile(configFilePath)
		if err != nil {
			fmt.Println("Could not read config file:", err.Error())
			return
		}

		// Parse configuration
		options := DraftAgentOptions{}
		err = json.Unmarshal(data, &options)
		if err != nil {
			fmt.Println("Could not parse config file:", err.Error())
			return
		}

		// Validate configuration
		if options.AuthToken == "" || options.BaseDataDirectory == "" || options.Domain == "" {
			fmt.Println("Invalid configuration. Please check the config file.")
			return
		}

		// Ensure lets encrypt email is set if https is enabled
		if !options.IsHttps && options.LetsEncryptEmail == "" {
			fmt.Println("Let's Encrypt email must be provided for HTTPS mode.")
			return
		}

		// Create and start Drift agent
		agent := NewDriftAgent(options)
		agent.Start()
		fmt.Println("Drift agent started. Press Ctrl+C to stop.")

		// Wait for graceful shutdown
		agent.WaitForGracefulShutdown()
	},
}
