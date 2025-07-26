package cmds

import (
	"fmt"
	"io"
	"net/http"

	"github.com/spf13/cobra"
)

func listModelsCommand() *cobra.Command {

	cmd := &cobra.Command{
		Use:   "list",
		Short: "List all models",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "models")
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

func getmodelsCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "get",
		Short: "Get a models",
		Run: func(cmd *cobra.Command, args []string) {
			resp, err := http.Get(apiBaseURL + "models/" + args[0])
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

func newModelsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "models",
		Short: "Manage models",
	}

	cmd.AddCommand(listModelsCommand())
	cmd.AddCommand(getmodelsCommand())

	return cmd
}
