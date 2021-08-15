package address

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"
)

func TestInit(t *testing.T) {
	res := parse(" .南安霞美土楼53..")
	fmt.Println(res)
	var x []string
	fmt.Println(x == nil)
}

// func BenchmarkParse(b *testing.B) {
// 	for i := 0; i < b.N; i++ {
// 		parse("福建省石狮市蚶江镇石湖城外二区3号")
// 	}
// }
// func Test(t *testing.T) {
// 	res, wor := nGramMatch("上海嘉定")
// 	fmt.Printf(res[0], wor[0])
// }

func TestParsing(t *testing.T) {
	fp, err := os.Open("test.csv")
	if err != nil {
		panic(err)
	}
	wr, err := os.Create("out.csv")
	if err != nil {
		panic(err)
	}
	s := time.Now()
	fr := bufio.NewReader(fp)
	count := 0
	errCount := 0
	for {
		line, err := fr.ReadString('\n')
		line = strings.Trim(line, "\n\r")
		if err != nil {
			break
		}
		add := parse(line)
		if add == "" {
			errCount++
			wr.WriteString(line + "," + "error" + "\n")
		} else {
			count++
			wr.WriteString(line + "," + add + "\n")
		}
	}
	fmt.Printf("finish in %d ms, count %d, err %d", time.Since(s).Milliseconds(), count, errCount)
	wr.Close()
}
