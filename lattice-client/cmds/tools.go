package cmds

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

func listToolsCommand() *cobra.Command {

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all tools",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "tools")
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

func getToolsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a tool",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "tools/" + args[0])
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

func deleteToolsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete a tool",
		Run: func(cmd *cobra.Command, args []string) {
			if len(args) < 1 {
				fmt.Println("Please provide a tool ID to delete.")
				return
			}
			req, err := http.NewRequest(http.MethodDelete, apiBaseURL+"tools"+"/"+args[0], nil)
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

func getFunctionCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get-function",
		Short: "Get functions of a tool",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "tool/functions/" + args[0])
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

func listFunctionsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list-functions",
		Short: "List all tool functions",
		Run: func(cmd *cobra.Command, args []string) {
			all, _ := cmd.Flags().GetBool("allfunctions")
			if all {
				resp, err := http.Get(apiBaseURL + "tool/functions")
				if err != nil {
					fmt.Println("Error:", err)
					return
				}
				defer resp.Body.Close()
				body, _ := io.ReadAll(resp.Body)
				fmt.Println(string(body))
			} else {
				fmt.Println("Use --allfunctions to list all tool functions.")
			}
		},
	}
	cmd.Flags().Bool("allfunctions", false, "Include all functions")
	return cmd
}

func createToolsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a new tool",
		Run: func(cmd *cobra.Command, args []string) {
			var id, description, jsonPath string

			fmt.Print("Tool ID: ")
			fmt.Scanln(&id)
			fmt.Print("Description (optional): ")
			fmt.Scanln(&description)
			fmt.Print("Path to tool list JSON file: ")
			fmt.Scanln(&jsonPath)

			toolListBytes, err := os.ReadFile(jsonPath)
			if err != nil {
				fmt.Println("Error reading JSON file:", err)
				return
			}
			// Validate JSON
			var tmp interface{}
			if err := json.Unmarshal(toolListBytes, &tmp); err != nil {
				fmt.Println("Invalid JSON:", err)
				return
			}

			payload := fmt.Sprintf(`{"id":"%s","description":"%s","toollist":%s}`, id, description, string(toolListBytes))
			resp, err := http.Post(apiBaseURL+"tools", "application/json", io.NopCloser(strings.NewReader(payload)))
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

func newToolsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "tools",
		Short: "Manage tools",
	}
	cmd.AddCommand(listToolsCommand())
	cmd.AddCommand(getToolsCommand())
	cmd.AddCommand(deleteToolsCommand())
	cmd.AddCommand(getFunctionCommand())
	cmd.AddCommand(listFunctionsCommand())
	cmd.AddCommand(createToolsCommand())

	return cmd
}
