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

func listAgentsCommand() *cobra.Command {

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all agents",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "agents")
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

func getAgentCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get an agent",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "agents/" + args[0])
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

func deleteAgentCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete an agent",
		Run: func(cmd *cobra.Command, args []string) {
			if len(args) < 1 {
				fmt.Println("Please provide a agent ID to delete.")
				return
			}
			req, err := http.NewRequest(http.MethodDelete, apiBaseURL+"agents"+"/"+args[0], nil)
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

func createAgentCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a new agent",
		Run: func(cmd *cobra.Command, args []string) {
			var id, prompt, recalltoolsPath string

			fmt.Print("Agent ID: ")
			fmt.Scanln(&id)
			fmt.Print("Prompt (optional): ")
			fmt.Scanln(&prompt)
			fmt.Print("Path to recalltools JSON file: ")
			fmt.Scanln(&recalltoolsPath)

			recalltoolsBytes, err := os.ReadFile(recalltoolsPath)
			if err != nil {
				fmt.Println("Error reading recalltools JSON file:", err)
				return
			}
			// Validate JSON
			var tmp interface{}
			if err := json.Unmarshal(recalltoolsBytes, &tmp); err != nil {
				fmt.Println("Invalid JSON:", err)
				return
			}

			printRecall, _ := cmd.Flags().GetBool("printrecall")
			if printRecall {
				fmt.Println("RecallTools JSON:")
				fmt.Println(string(recalltoolsBytes))
			}

			payload := fmt.Sprintf(`{"id":"%s","prompt":"%s","recalltools":%s}`, id, prompt, string(recalltoolsBytes))
			resp, err := http.Post(apiBaseURL+"agents", "application/json", strings.NewReader(payload))
			if err != nil {
				fmt.Println("Error:", err)
				return
			}
			defer resp.Body.Close()
			body, _ := io.ReadAll(resp.Body)
			fmt.Println(string(body))
		},
	}
	cmd.Flags().Bool("printrecall", false, "Print recalltools JSON before sending")
	return cmd
}

func newAgentsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "agents",
		Short: "Manage agents",
	}
	cmd.AddCommand(
		listAgentsCommand(),
		getAgentCommand(),
		deleteAgentCommand(),
		createAgentCommand(),
	)
	return cmd
}
