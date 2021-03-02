package main

import (
	"bufio"
	"fmt"
	"os"
)

var squishyFile string

func main() {
	processArgs(os.Args[1:])

	if squishyFile == "" {
		squishyFile = "squishy"
	}

	file, err := os.Open(squishyFile)

	if err != nil {
		fmt.Println("Error: Could not open squishy file: " + squishyFile)
		os.Exit(2)
	}

	defer file.Close()

	var lines []string

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}

	if scanner.Err() != nil {
		fmt.Println("Error: Reading file : " + squishyFile + " caused error" + scanner.Err().Error())
		os.Exit(2)
	}

	fmt.Println(lines)

	processLines(lines)
}

func processArgs(argsToProcess []string) {
	for i := 0; i < len(argsToProcess); i++ {

		thisArg := argsToProcess[i]

		if thisArg == "--squishy" {
			squishyFile = argsToProcess[i+1]
			i++
		}
	}
}

func processLines(lines []string) {
	//var Output string
	//var Main []string
	//var Module []string
	//var ModulePath []string

}
