package main

import (
	"lattice-client/cmds"
)

func main() {
	cmds.Execute()
	// The Execute function in cmds package will handle the command line interface
	// and route commands to the appropriate handlers.
}
