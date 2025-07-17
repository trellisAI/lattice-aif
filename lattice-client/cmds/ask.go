package cmds

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

type ChatMessage struct {
	Role    string   `json:"role"`
	Content string   `json:"content"`
	Images  []string `json:"images,omitempty"`
}

type ChatRequest struct {
	Tag      string                 `json:"tag"`
	Model    string                 `json:"model"`
	Messages []ChatMessage          `json:"messages"`
	Stream   bool                   `json:"stream,omitempty"`
	Options  map[string]interface{} `json:"options,omitempty"`
	Template string                 `json:"template,omitempty"`
	Format   string                 `json:"format,omitempty"`
}

func newAskCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "chat",
		Short: "Ask a question to the LatticeAI",
		Run: func(cmd *cobra.Command, args []string) {
			reader := bufio.NewReader(os.Stdin)
			fmt.Print("Agent tag: ")
			tag, _ := reader.ReadString('\n')
			tag = strings.TrimSpace(tag)

			fmt.Print("LLM model: ")
			model, _ := reader.ReadString('\n')
			model = strings.TrimSpace(model)

			var messages []ChatMessage

			fmt.Println("Enter your messages. Type 'exit' to quit.")
			for {
				fmt.Print("> ")
				content, _ := reader.ReadString('\n')
				content = strings.TrimSpace(content)
				if content == "exit" {
					break
				}
				messages = append(messages, ChatMessage{
					Role:    "user",
					Content: content,
				})

				req := ChatRequest{
					Tag:      tag,
					Model:    model,
					Messages: messages,
				}
				payload, _ := json.Marshal(req)
				resp, err := http.Post(apiBaseURL+"chat", "application/json", bytes.NewReader(payload))
				if err != nil {
					fmt.Println("Error:", err)
					continue
				}
				body, _ := io.ReadAll(resp.Body)
				resp.Body.Close()

				var result map[string]interface{}
				if err := json.Unmarshal(body, &result); err != nil {
					fmt.Println("Error parsing response:", err)
					continue
				}
				if msg, ok := result["message"].(map[string]interface{}); ok {
					if content, ok := msg["content"].(string); ok {
						fmt.Println("Assistant:", content)
						messages = append(messages, ChatMessage{
							Role:    "assistant",
							Content: content,
						})
					}
				} else {
					fmt.Println("Unexpected response:", string(body))
				}
			}
		},
	}
	return cmd
}
