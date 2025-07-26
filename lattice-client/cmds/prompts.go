package cmds

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

func listPromptsCommand() *cobra.Command {

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all prompts",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "prompts")
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

func getPromptCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a prompt",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "prompts/" + args[0])
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

func deletePromptCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "delete",
		Short: "Delete a prompt",
		Run: func(cmd *cobra.Command, args []string) {
			if len(args) < 1 {
				fmt.Println("Please provide a prompt ID to delete.")
				return
			}
			req, err := http.NewRequest(http.MethodDelete, apiBaseURL+"prompts"+"/"+args[0], nil)
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

func createPromptCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "create",
		Short: "Create a new prompt",
		Run: func(cmd *cobra.Command, args []string) {
			var id string
			fmt.Print("Prompt ID: ")
			fmt.Scanln(&id)

			fmt.Println("Enter prompt text (end with an empty line):")
			scanner := bufio.NewScanner(os.Stdin)
			var lines []string
			for scanner.Scan() {
				line := scanner.Text()
				if line == "" {
					break
				}
				lines = append(lines, line)
			}
			prompt := strings.Join(lines, "\n")

			payload := fmt.Sprintf(`{"id":"%s","prompt":"%s"}`, id, prompt)
			resp, err := http.Post(apiBaseURL+"prompts", "application/json", io.NopCloser(strings.NewReader(payload)))
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

func newPromptsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "prompts",
		Short: "Manage prompts",
	}
	cmd.AddCommand(listPromptsCommand())
	cmd.AddCommand(getPromptCommand())
	cmd.AddCommand(deletePromptCommand())
	cmd.AddCommand(createPromptCommand())
	return cmd
}
