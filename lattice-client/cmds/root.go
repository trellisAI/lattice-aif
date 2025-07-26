package cmds

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
	"github.com/spf13/cobra"
)

// read from the config file or environment variable
var (
	apiKey     string
	apiBaseURL string
)

type clientConfig struct {
	ApiKey string `toml:"api_key"`
	Url    string `toml:"url"`
}

func init() {

	apiKey = os.Getenv("LATTICE_API_KEY")
	apiBaseURL = os.Getenv("LATTICE_API_BASE_URL")

	if apiKey == "" || apiBaseURL == "" {
		var homeDir string
		if os.Getenv("USERPROFILE") != "" {
			homeDir = os.Getenv("USERPROFILE")
		} else {
			homeDir = os.Getenv("HOME")
		}
		configPath := filepath.Join(homeDir, ".Lattice", "client", "config.toml")
		var cfg clientConfig
		if _, err := os.Stat(configPath); err == nil {
			if _, err := toml.DecodeFile(configPath, &cfg); err == nil {
				if apiKey == "" {
					apiKey = cfg.ApiKey
				}
				if apiBaseURL == "" {
					apiBaseURL = cfg.Url
				}
			}
		}
	}
}

type command struct {
	name string
	cmd  *cobra.Command
}

func Execute() {
	var rootCmd = &cobra.Command{
		Use:   "lattice",
		Short: "CLI for LatticeAI OpenAPI endpoints",
	}

	commands := []command{
		{"connections", newConnectionsCmd()},
		{"prompts", newPromptsCmd()},
		{"models", newModelsCmd()},
		{"tools", newToolsCmd()},
		{"agents", newAgentsCmd()},
	}
	for _, c := range commands {
		rootCmd.AddCommand(c.cmd)
	}
	rootCmd.CompletionOptions.DisableDefaultCmd = true
	rootCmd.AddCommand(newConfigCmd())
	rootCmd.AddCommand(newAskCmd())
	rootCmd.AddCommand(&cobra.Command{
		Use:   "version",
		Short: "Show the version of the LatticeAI CLI",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println("LatticeAI CLI version 0.1.0")
		},
	})

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
