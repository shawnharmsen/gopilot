package main

import "C"
import (
	"encoding/json"
	"fmt"
	"go/parser"
	"go/scanner"
	"go/token"
)

type Offset [2]int

func (of Offset) Start() int {
	return of[0]
}

func (of Offset) End() int {
	return of[1]
}

func (of Offset) Len() int {
	return of[1] - of[0]
}

type ScanResult struct {
	Offsets  []Offset `json:"offsets"`
	IDs      []int    `json:"ids"`
	Names    []string `json:"names"`
	Literals []string `json:"literals"`
}

const (
	SPACE = iota + token.TILDE + 1
	NEWLINE
	TAB
)

//export Scan
func Scan(byteSequence *C.char) *C.char {
	sequence := C.GoString(byteSequence)
	fset := token.NewFileSet()
	file := fset.AddFile("", fset.Base(), len(sequence))

	var s scanner.Scanner
	s.Init(file, []byte(sequence), nil, scanner.ScanComments)

	rawResults := ScanResult{}

	for {
		pos, tok, lit := s.Scan()
		if tok == token.EOF {
			break
		}
		startPos := fset.Position(pos).Offset
		if len(lit) == 0 {
			lit = tok.String()
		}
		offset := Offset{startPos, startPos + len(lit)}
		rawResults.Offsets = append(rawResults.Offsets, offset)
		rawResults.IDs = append(rawResults.IDs, int(tok))
		rawResults.Names = append(rawResults.Names, tok.String())
		rawResults.Literals = append(rawResults.Literals, lit)
	}

	// Post-process the scanned tokens to handle whitespaces and normalize the
	// output.
	results := ScanResult{}
	for i := 0; i < len(rawResults.IDs); i++ {
		// If some tokens' offsets are discontinuous, we need to fill the gap
		// with whitespaces.
		if i > 0 && rawResults.Offsets[i].Start() > rawResults.Offsets[i-1].End() {
			// For each character in the gap.
			for j := rawResults.Offsets[i-1].End(); j < rawResults.Offsets[i].Start(); j++ {
				switch sequence[j] {
				case ' ':
					results.Offsets = append(results.Offsets, [2]int{j, j + 1})
					results.IDs = append(results.IDs, int(SPACE))
					results.Names = append(results.Names, "SPACE")
					results.Literals = append(results.Literals, " ")
				case '\n':
					results.Offsets = append(results.Offsets, [2]int{j, j + 1})
					results.IDs = append(results.IDs, int(NEWLINE))
					results.Names = append(results.Names, "NEWLINE")
					results.Literals = append(results.Literals, "\n")
				case '\t':
					results.Offsets = append(results.Offsets, [2]int{j, j + 1})
					results.IDs = append(results.IDs, int(TAB))
					results.Names = append(results.Names, "TAB")
					results.Literals = append(results.Literals, "\t")
				case '\r':
					// Ignore carriage return.
				default:
					return C.CString(fmt.Sprintf("Unexpected character %q at offset %d", sequence[j], j))
				}
			}
		}
		results.Offsets = append(results.Offsets, rawResults.Offsets[i])
		results.IDs = append(results.IDs, rawResults.IDs[i])
		results.Names = append(results.Names, rawResults.Names[i])
		results.Literals = append(results.Literals, rawResults.Literals[i])
	}

	// Marshal the result into JSON
	resultsBytes, err := json.Marshal(results)
	if err != nil {
		return C.CString(err.Error())
	}

	return C.CString(string(resultsBytes))
}

//export Parse
func Parse(byteSequence *C.char) *C.char {
	sequence := C.GoString(byteSequence)
	fset := token.NewFileSet()

	parsedFile, err := parser.ParseFile(fset, "", sequence, parser.ParseComments)
	if err != nil {
		return C.CString(err.Error())
	}

	// Marshal the result into JSON
	bytes, err := json.Marshal(parsedFile)
	if err != nil {
		return C.CString(err.Error())
	}
	return C.CString(string(bytes))
}

//export IDToTokenName
func IDToTokenName(id C.int) *C.char {
	if int(id) <= int(token.TILDE) {
		return C.CString(token.Token(int(id)).String())
	}
	switch token.Token(int(id)) {
	case SPACE:
		return C.CString("SPACE")
	case NEWLINE:
		return C.CString("NEWLINE")
	case TAB:
		return C.CString("TAB")
	}
	return C.CString("UNKNOWN")
}

//export IDToTokenLiteral
func IDToTokenLiteral(id C.int) *C.char {
	if int(id) <= int(token.TILDE) {
		return C.CString(token.Token(int(id)).String())
	}
	switch token.Token(int(id)) {
	case SPACE:
		return C.CString(" ")
	case NEWLINE:
		return C.CString("\n")
	case TAB:
		return C.CString("\t")
	}
	return C.CString("")
}

func main() {}
