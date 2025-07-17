package cmds

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

func ServerConfigCmd() *cobra.Command {
	// This command allows users to set the API key and URL for the LatticeAI server
	server := &cobra.Command{
		Use:   "server",
		Short: "Configure the LatticeAI server",
	}

	server.Flags().String("api-key", "", "API key for LatticeAI")
	server.Flags().String("url", "http://localhost:44444/", "API URL for latticeai-server")

	server.Run = func(cmd *cobra.Command, args []string) {
		apiKey, _ := cmd.Flags().GetString("api-key")
		url, _ := cmd.Flags().GetString("url")

		if apiKey == "" {
			fmt.Print("Enter API key (default: none): ")
			var input string
			fmt.Scanln(&input)
			if input != "" {
				apiKey = input
			}
		}
		if url == "" || url == "http://localhost:44444/" {
			fmt.Print("Enter API URL (default: http://localhost:44444/): ")
			var input string
			fmt.Scanln(&input)
			if input != "" {
				url = input
			}
		}
		os.Setenv("LATTICE_API_KEY", apiKey)
		os.Setenv("LATTICE_API_URL", url)

		// Save config to .Lattice/client/config.toml
		var homeDir string
		if os.Getenv("USERPROFILE") != "" {
			homeDir = os.Getenv("USERPROFILE")
		} else {
			homeDir = os.Getenv("HOME")
		}
		latticeDir := homeDir + string(os.PathSeparator) + ".Lattice"
		clientDir := latticeDir + string(os.PathSeparator) + "client"
		configPath := clientDir + string(os.PathSeparator) + "config.toml"
		if _, err := os.Stat(clientDir); os.IsNotExist(err) {
			err := os.MkdirAll(clientDir, 0755)
			if err != nil {
				fmt.Println("Error creating config directory:", err)
				return
			}
		}
		configContent := fmt.Sprintf("api_key = \"%s\"\nurl = \"%s\"\n", apiKey, url)
		f, err := os.Create(configPath)
		if err != nil {
			fmt.Println("Error writing config file:", err)
			return
		}
		defer f.Close()
		_, err = f.WriteString(configContent)
		if err != nil {
			fmt.Println("Error saving config:", err)
			return
		}
		fmt.Println("Configuration set:")
		fmt.Println("API Key:", apiKey)
		fmt.Println("API URL:", url)
		fmt.Println("Config saved to:", configPath)
	}
	return server
}

func newConfigCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Configure the LatticeAI CLI",
	}
	cmd.AddCommand(ServerConfigCmd())
	return cmd
}
