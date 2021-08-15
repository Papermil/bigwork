package address

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

//go:embed data.json
var addressData []byte

type addDataItem struct {
	Code string
	Name string
}

//构建多值字典，使得同一简称能对应多个地址代码
type Multimap map[string][]string

// type keyValues struct {
// 	key    string
// 	values []string
// }

func (multimap Multimap) Add(key, value string) {
	if len(multimap[key]) == 0 {
		multimap[key] = []string{value}
	} else {
		multimap[key] = append(multimap[key], value)
	}
}

func (multimap Multimap) Get(key string) []string {
	if multimap == nil {
		return nil
	}
	values := multimap[key]
	return values
}

func InSliceString(e string, slice []string) bool {
	for _, s := range slice {
		if s == e {
			return true
		}
	}
	return false
}

var codeMap = map[string]string{}
var indexMap = make(Multimap)
var indexMaxLen = 0

var nationClean = regexp.MustCompile(`(蒙古族|回族|藏族|维吾尔族|苗族|彝族|壮族|布依族|朝鲜族|满族|侗族|瑶族|白族|土家族|哈尼族|哈萨克族|傣族|黎族|僳僳族|佤族|畲族|高山族|拉祜族|水族|东乡族|纳西族|景颇族|柯尔克孜族|土族|达斡尔族|仫佬族|羌族|布朗族|撒拉族|毛南族|仡佬族|锡伯族|阿昌族|普米族|塔吉克族|怒族|乌孜别克族|俄罗斯族|鄂温克族|德昂族|保安族|裕固族|京族|塔塔尔族|独龙族|鄂伦春族|赫哲族|门巴族|珞巴族|基诺族).*`)

var trimExp = regexp.MustCompile("(综合|村|省|县|开发区|区|市|镇|乡|路街道|街道|第二|第一|第三|(农)场|花园|市辖区|辖|地区|管委会|直辖县级行政区|(社区)(居民)居委会|自治(州|县|区)|村委会|经济综合实验区|(前|中|后)旗|示范区)$")

//获得地址简称
//输入：地址全称（字符串）      输出：地址简称（字符串）
func processIndex(in string) string {
	if len([]rune(in)) > 2 {
		in = trimExp.ReplaceAllString(in, "")
		in = nationClean.ReplaceAllString(in, "")
	}
	return in
}

//构建地址全/简称-地址代码双向索引
func init() {
	var data []addDataItem
	var cod1 strings.Builder
	var cod2 strings.Builder
	err := json.Unmarshal(addressData, &data)
	if err != nil {
		panic(err)
	}
	for _, add := range data {
		codeMap[add.Code] = add.Name
		if len([]rune(add.Name)) == 1 {
			continue
		}
		index := processIndex(add.Name)
		cod1.WriteString(add.Code)
		cod1.WriteString("1")
		cod2.WriteString(add.Code)
		cod2.WriteString("0")
		if index == add.Name {
			indexMap.Add(add.Name, cod1.String())
		} else {
			indexMap.Add(add.Name, cod1.String())
			indexMap.Add(index, cod2.String())
		}
		if len([]rune(index)) > indexMaxLen {
			indexMaxLen = len([]rune(index))
		}
		cod1.Reset()
		cod2.Reset()
	}
}

//ngram分词，按最长匹配原则获得地址代码集合
//输入：地址（字符串）      输出：地址代码集合（字符数组），识别到的地址集合（字符数组）
func nGramMatch(s string) ([]string, []string) {
	r := []rune(s)
	l := len(r)
	var rank = 6
	var cod1 strings.Builder
	result := make([]string, 0, 10)
	words := make([]string, 0, 7)
	for i := 0; i < l; i++ {
		if len(words) == 7 {
			goto break2
		}
		for j := indexMaxLen; j >= 2; j-- {
			if i+j > l {
				continue
			}
			seg := r[i : i+j]
			//很耗时
			re := indexMap[string(seg)]
			if re != nil {
				if InSliceString(string(r), words) {
					i += j - 1
					goto break2
				}
				words = append(words, string(seg))
				if rank > 0 {
					for k := 0; k < len(indexMap[string(seg)]); k++ {
						cod1.WriteString(re[k])
						cod1.WriteString(fmt.Sprint(rank))
						result = append(result, cod1.String())
						cod1.Reset()
					}
				} else {
					for k := 0; k < len(indexMap[string(seg)]); k++ {
						cod1.WriteString(re[k])
						cod1.WriteString("0")
						result = append(result, cod1.String())
						cod1.Reset()
					}
				}
				rank -= 1
				i += j - 1
				goto break2
			}
		}
	break2:
	}
	return result, words
}

//判断某地址代码代表的地址等级
func isProvince(code string) bool {
	return code[2:9] == "0000000"
}
func isCity(code string) bool {
	return code[4:9] == "00000" && code[2:4] != "00"
}
func isCounty(code string) bool {
	return code[4:6] != "00" && code[6:9] == "000"
}

// func isTown(code string) bool {
// 	return code[6:9] != "000"
// }

//计算某地址代码的地址等级
func RankCalcu(code string) int {
	if isProvince(code) {
		return 1
	} else if isCity(code) {
		return 2
	} else if isCounty(code) {
		return 3
	} else {
		return 4
	}
}

//判断两个字符串是否冲突
func checkPart(p1 string, p2 string) string {
	if p1 == "00" {
		return p2
	}
	if p2 == "00" {
		return p1
	}
	if p1 == p2 {
		return p1
	}
	return ""
}

//判断两个地址代码是否冲突
func checkCode(x string, y string) int {
	var conflict = 0
	var p = "00"
	p = checkPart(p, x[0:2])
	p = checkPart(p, y[0:2])
	if p == "" {
		conflict += 1
	}
	var c = "00"
	c = checkPart(c, x[2:4])
	c = checkPart(c, y[2:4])
	if c == "" {
		conflict += 1
	}
	var co = "00"
	co = checkPart(co, x[4:6])
	co = checkPart(co, y[4:6])
	if co == "" {
		conflict += 1
	}

	return conflict
}

//string转int
func toint(s byte) int {
	d := string(s)
	num, _ := strconv.Atoi(d)
	return num
}

//根据集合中的地址代码计算整个地址集合的置信度
//输入：地址代码集合（字符数组）      输出：置信度（int整数）
func CalcuConfidential(codes []string) int {
	var conf = 0
	for _, i := range codes {
		conf += RankCalcu(i) - 4
		conf -= (toint(i[9])) * (toint(i[10]))
		if i[10] == '6' {
			conf -= toint(i[10]) * 7
		} else {
			conf -= toint(i[10]) * 5
		}
	}

	return conf
}

//判断某集合中是否已有某个地址代码
func checkonly(temp []string, code string) bool {
	for i := 0; i < len(temp); i++ {
		if temp[i][len(temp)-1] == code[len(code)-1] {
			return true
		}
	}
	return false
}

//根据结果地址代码集合读取三级行政地址
//输入：结果地址代码集合（字符数组）      输出：三级地址（字符串）
func readResult(codes []string) string {
	var code = "00000000000"
	var p, c, co string
	for i := 0; i < len(codes); i++ {
		if checkCode(code, codes[i]) == 0 {
			code = codes[i]
		}
	}
	// fmt.Printf("finalcode:",code)
	if code[0:2] != "00" {
		p = codeMap[code[0:2]+"0000000"]
	} else {
		p = ""
	}
	if code[2:4] != "00" {
		c = codeMap[code[0:4]+"00000"]
	} else {
		c = ""
	}
	if c == "市辖区" || c == "县" {
		c = ""
	}
	if code[4:6] != "00" {
		co = codeMap[code[0:6]+"000"]
	} else {
		co = ""
	}
	return p + c + co
}

//对识别结果进行过滤，减少假阳性
//输入：结果地址代码集合（字符数组），分词识别到的地址集合（字符数组）      输出：地址代码集合（字符数组）
func judgeResult(result []string, words []string) []string {
	var l = len(words)
	if l == 1 || len(result) == 1 {
		for i := 0; i < len(result); i++ {
			for j := 0; j < len(words); j++ {
				if codeMap[result[i][0:9]] == words[j] && words[j] != "开发区" {
					res := make([]string, 0, 1)
					res = append(res, result[i])
					return res
				}
			}
		}
		return nil
	}
	return result
}

//重构sort排序，根据自定义规则对分词获得的代码集合进行排序
type addresscodes []string

func (a addresscodes) Len() int {
	return len(a)
}
func (a addresscodes) Swap(i, j int) {
	a[i], a[j] = a[j], a[i]
}
func (a addresscodes) Less(i, j int) bool {
	var res = 0
	if a[i][0:2] > a[j][0:2] {
		res = -1
	} else if a[i][0:2] < a[j][0:2] {
		res = 1
	} else {
		if RankCalcu(a[i]) > RankCalcu(a[j]) {
			res = -1
		} else if RankCalcu(a[i]) < RankCalcu(a[j]) {
			res = 1
		} else if RankCalcu(a[i]) == RankCalcu(a[j]) {
			if a[i][10] > a[j][10] {
				res = 1
			} else if a[i][10] < a[j][10] {
				res = -1
			} else {
				res = 0
			}
		}
	}
	if res == -1 {
		return false
	} else if res == 1 {
		return true
	} else {
		return a[i] < a[j]
	}
}

//寻优算法，按行读取排序后的分词结果代码集合，将不冲突的地址代码放进一个集合，返回置信度最高/地址最完整的集合
//输入：排序后的地址代码集合（字符数组）      输出：最优地址代码集合（字符数组）
func choosebest(candidate []string) []string {
	var p = "00"
	var c = "00"
	var co = "00"
	temp := make([]string, 0, 4)
	wait := make([]string, 0, 2)
	result := make([]string, 0, 4)
	for _, i := range candidate {
		p = checkPart(p, i[0:2])
		c = checkPart(c, i[2:4])
		co = checkPart(co, i[4:6])
		if p != "" && c != "" && co != "" {
			if len(temp) == 0 {
				temp = append(temp, i)
			} else {
				if CalcuConfidential([]string{temp[len(temp)-1]}) > CalcuConfidential([]string{i}) {
					if temp[len(temp)-1][10] != i[10] && !checkonly(temp, i) {
						if RankCalcu(temp[len(temp)-1]) == RankCalcu(i) {
							temp[len(temp)-1] = i
						} else {
							if toint(temp[len(temp)-1][10])-toint(i[10]) <= 2 {
								temp = append(temp, i)
							}
						}
					}
				} else {
					if RankCalcu(temp[len(temp)-1]) != RankCalcu(i) && !checkonly(temp, i) {
						if toint(temp[len(temp)-1][10])-toint(i[10]) <= 2 {
							temp = append(temp, i)
						}
					}
				}
				p = temp[len(temp)-1][0:2]
				c = temp[len(temp)-1][2:4]
				co = temp[len(temp)-1][4:6]
			}
		} else {
			if i[0:2] != temp[0][0:2] {
				if CalcuConfidential(result) <= CalcuConfidential(temp) {
					if len(result) != 0 && len(temp) >= 3 && temp[0] != result[0] {
						return temp
					}
				} else {
					if len(result) <= 2 {
						result = result[0:0]
						result = append(result, temp...)
					} else if len(result) == len(temp) && len(result) == 3 {
						return nil
					}
				}
				temp = temp[0:0]
				temp = append(temp, i)
				p = i[0:2]
				c = i[2:4]
				co = i[4:6]
			} else {
				if CalcuConfidential([]string{temp[len(temp)-1]}) > CalcuConfidential([]string{i}) {
					if temp[len(temp)-1][10] != i[10] && !checkonly(temp, i) {
						temp[len(temp)-1] = i
						p = i[0:2]
						c = i[2:4]
						co = i[4:6]
					}
				} else if CalcuConfidential([]string{temp[len(temp)-1]}) == CalcuConfidential([]string{i}) {
					if RankCalcu(temp[len(temp)-1]) > RankCalcu(i) && !checkonly(temp, i) {
						temp[len(temp)-1] = i
						p = i[0:2]
						c = i[2:4]
						co = i[4:6]
					}
				} else {
					if len(wait) == 0 {
						wait = append(wait, i)
					} else if len(wait) == 1 {
						if checkCode(wait[0], i) == 0 {
							if RankCalcu(wait[0]) < RankCalcu(i) && !checkonly(wait, i) {
								wait = append(wait, i)
							}
						} else {
							wait[0] = i
						}
					}
					if len(wait) == 2 {
						if wait[0][0:2] == temp[0][0:2] {
							temp[len(temp)-1] = wait[0]
							temp = append(temp, wait[1])
						}
						wait = wait[0:0]
					}
					p = temp[len(temp)-1][0:2]
					c = temp[len(temp)-1][2:4]
					co = temp[len(temp)-1][4:6]
				}
			}
		}
		// fmt.Println(result, temp, i, wait, CalcuConfidential(result), CalcuConfidential(temp), CalcuConfidential([]string{i}), CalcuConfidential(wait))
	}
	if CalcuConfidential(result) <= CalcuConfidential(temp) {
		if len(result) != 0 && len(temp) >= 3 && temp[0] != result[0] {
			return temp
		}
	} else {
		if len(result) <= len(temp) {
			result = result[0:0]
			result = append(result, temp...)
		} else if len(result) == len(temp) && len(result) == 3 {
			return nil
		}
	}
	return result
}

//根据输入的地址字符串，进行分词排序寻优，得到最可信的三级地址
//输入：地址（字符串）      输出：三级地址（字符串）
func parse(s string) string {
	res, wor := nGramMatch(s)
	if res == nil {
		return ""
	}
	sort.Sort(addresscodes(res))
	// for _, i := range res {
	// 	fmt.Println(i, ":", codeMap[i[0:9]])
	// }
	result := choosebest(res)
	if res == nil {
		return ""
	}
	result = judgeResult(result, wor)
	if res == nil {
		return ""
	}
	final := readResult(result)
	return final
}
