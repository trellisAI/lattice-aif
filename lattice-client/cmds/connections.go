package cmds

import (
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/spf13/cobra"
)

func createConnectionCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a new connection",
		Run: func(cmd *cobra.Command, args []string) {
			var id, source, url, apiKey string

			fmt.Print("Connection ID: ")
			fmt.Scanln(&id)
			fmt.Print("Source (default: ollama): ")
			fmt.Scanln(&source)
			if source == "" {
				source = "ollama"
			}
			fmt.Print("URL: ")
			fmt.Scanln(&url)
			fmt.Print("API Key (optional): ")
			fmt.Scanln(&apiKey)

			payload := fmt.Sprintf(`{"id":"%s","source":"%s","url":"%s","api_key":"%s"}`, id, source, url, apiKey)
			resp, err := http.Post(apiBaseURL+"connections", "application/json", io.NopCloser(strings.NewReader(payload)))
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Println(string(body))
		},
	}
	return cmd
}

func listConnectionsCommand() *cobra.Command {

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all connections",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "connections")
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Println(string(body))
		},
	}
	// Add get, create, delete subcommands as needed
	return cmd
}

func getConnectionCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a connection",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "connections/" + args[0])
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Println(string(body))
		},
	}
	return cmd
}

func deleteConnectionCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete a connection",
		Run: func(cmd *cobra.Command, args []string) {
			if len(args) < 1 {
				fmt.Println("Please provide a connection ID to delete.")
				return
			}
			req, err := http.NewRequest(http.MethodDelete, apiBaseURL+"connections"+"/"+args[0], nil)
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			resp, err := http.DefaultClient.Do(req)
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Println(string(body))
		},
	}
	return cmd
}

func newConnectionsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "connections",
		Short: "Manage LLM connections",
	}

	cmd.AddCommand(listConnectionsCommand())
	cmd.AddCommand(getConnectionCommand())
	cmd.AddCommand(deleteConnectionCommand())
	cmd.AddCommand(createConnectionCommand())

	return cmd
}
