package main

import (
	"github.com/spf13/cobra"
)

// Make sure to place the executable in /usr/local/bin or /usr/bin

var rootCmd = &cobra.Command{
	Use:   "driftctl",
	Short: "Driftctl is an CLI to manage chromium instances for running ui tests.",
	Long:  `Driftctl is an CLI to manage chromium instances for running ui tests.`,
	Run: func(cmd *cobra.Command, args []string) {
		cmd.Help()
	},
}

func main() {
	rootCmd.Execute()
}
