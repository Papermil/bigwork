import re
import json
import copy
import time
import pandas as pd
from functools import cmp_to_key
import getopt
import sys

indexMap={}
codeMap={}
indexMaxLen=0

def processIndex(key):
    race_regex = re.compile(r"(汉族|仫佬族|黎族|土家族|蒙古族|羌族|僳僳族|哈尼族|回族|布朗族|佤族|哈萨克族\
|藏族|撒拉族|畲族|傣族|维吾尔族|毛南族|高山族|德昂族|苗族|仡佬族|拉祜族|保安族|彝族|锡伯族|水族|裕固族|壮族|阿昌族|东乡族|京族|\
|布依族|普米族|纳西族|独龙族|朝鲜族|塔吉克族|景颇族|鄂伦春族|满族|怒族|柯尔克孜族|赫哲族|侗族|乌孜别克族|土族|门巴族\
|瑶族|俄罗斯族|达斡尔族|珞巴族|白族|鄂温克族|塔塔尔族|基诺族)+.*")
    address_regex = re.compile(
        r"(综合|村|省|县|开发区|区|市|镇|乡|路街道|街道|第二|第一|第三|(农)场|花园|市辖区|辖|地区|管委会|直辖县级行政区|(社区)(居民)居委会|自治(州|县|区)|村委会|经济综合实验区|(前|中|后)旗|示范区)+$"  #开发区先不去
    )
    if len(key) > 2:
        return re.sub(race_regex, '', re.sub(address_regex, '', key))
    else:
        return key

def cleanwords(s):
    result = re.findall('[\u4e00-\u9fa5a]+', str(s), re.S)
    chinese = "".join(result)
    return chinese

def init():
    global indexMaxLen,indexMap,codeMap
    with open("four_level_area1.json", 'r', encoding='utf-8') as f:
        list = json.load(f)
    for i in list:
        indexMap[processIndex(i['Name'])] = []
        indexMap[i['Name']] = []
        codeMap[i['Code']] = i['Name']
    for i in list:
        if processIndex(i['Name'])==i['Name']:
            indexMap[processIndex(i['Name'])].append(i['Code']+'1')
        else:
            indexMap[processIndex(i['Name'])].append(i['Code']+'0')
            indexMap[i['Name']].append(i['Code']+'1')
        if len(i['Name'])>indexMaxLen:
            indexMaxLen=len(i['Name'])

def nGramMatch(s):
    s=cleanwords(s)
    # print(s)
    l=len(str(s))
    result=[]
    words=[]
    finalresult=[]
    i=0
    rank=6
    while i<=l-2:
        for j in range(indexMaxLen,1,-1):
            if i+j>l:
                continue
            try:
                re=indexMap[str(s)[i:i+j]]
                # if i>=2 and len(result)==0 and is_Chinese(s[i-1]) and is_Chinese(s[i-2]):
                #     return result, words
                if str(s)[i:i+j] in words:
                    i += j - 1
                    break

                words.append(str(s)[i:i+j])
                if rank>0:
                    result.extend([x+str(rank) for x in re])
                else:
                    result.extend([x + '0' for x in re])
                rank-=1
                # print(str(s)[i:i + j], re)
                i+=j-1
                break
            except KeyError:
                pass
        i+=1
        if len(words) == 7:
            break
        finalresult=list(set(result))
        finalresult.sort(key=result.index)
    return finalresult,words

def isProvince(code):
    return code[2:9]=='0000000'
def isCity(code):
    return code[4:9]=='00000' and code[2:4]!='00'
def isCounty(code):
    return code[4:6]!='00' and code[6:9]=='000'
def isTown(code):
    return code[6:9]!='000'

def RankCalcu(code):
    if isProvince(code):
        return 1
    elif isCity(code):
        return 2
    elif isCounty(code):
        return 3
    else:
        return 4

def checkPart(p1,p2):
    if p1=='00':
        return p2
    if p2=='00':
        return p1
    if p1==p2:
        return p1
    return ''

def checkCode(x, y):
    conflict=0
    p='00'
    p = checkPart(p, x[0:2])
    p = checkPart(p, y[0:2])
    if p=='':
        conflict+=1
    c='00'
    c = checkPart(c, x[2:4])
    c = checkPart(c, y[2:4])
    if c=='':
        conflict+=1
    co='00'
    co = checkPart(co, x[4:6])
    co = checkPart(co, y[4:6])
    if co=='':
        conflict+=1

    return conflict

def custom_sort(preprocess_func=lambda x: x):
    def sort_func(x, y):
        if x[0:2] > y[0:2]:
            return 1
        elif x[0:2] < y[0:2]:
            return -1
        elif x[0:2] == y[0:2]:
            if RankCalcu(x) > RankCalcu(y):
                return 1
            elif RankCalcu(x) < RankCalcu(y):
                return -1
            elif RankCalcu(x) == RankCalcu(y):
                if x[10]>y[10]:
                    return -1
                elif x[10]<y[10]:
                    return 1
                else:
                    if x > y:
                        return 1
                    elif x < y:
                        return -1
                    else:
                        return 0
    return sort_func

def CalcuConfidential(codes):
    conf=0
    for i in codes:
        conf+=RankCalcu(i)-4
        conf-=(int(i[9]))*(int(i[10]))
        if i[10]=='6':
            conf-=int(i[10])*7
        else:
            conf -= int(i[10]) * 5
    return conf

def checkonly(temp,code):
    for i in temp:
        if i[-1]==code[-1]:
            return True
    return False

def choosebest(candidate):
    p = '00'
    c = '00'
    co = '00'
    temp = []
    wait=[]
    result = []
    for i in candidate:
        p = checkPart(p, i[0:2])
        c = checkPart(c, i[2:4])
        co = checkPart(co, i[4:6])
        if p != '' and c != '' and co != '':
            if len(temp)==0:
                temp.append(i)
            else:
                if CalcuConfidential([temp[-1]])>CalcuConfidential([i]):
                    if temp[-1][10]!=i[10] and not checkonly(temp,i):
                        if RankCalcu(temp[-1])==RankCalcu(i):
                            temp[-1]=i
                        else:
                            if int(temp[-1][10])-int(i[10])<=2:
                                temp.append(i)
                else:
                    if RankCalcu(temp[-1])!=RankCalcu(i) and not checkonly(temp,i):
                        if int(temp[-1][10]) - int(i[10]) <= 2:
                            temp.append(i)
                p = temp[-1][0:2]
                c = temp[-1][2:4]
                co = temp[-1][4:6]
        else:
            if i[0:2]!=temp[0][0:2]:
                if CalcuConfidential(result) <= CalcuConfidential(temp):
                    if len(result) == 0:
                        pass
                    elif len(temp) >= 3 and temp[0] != result[0]:
                        return temp
                    else:
                        pass
                else:
                    if len(result)<=2:
                        result = copy.deepcopy(temp)
                    elif len(result)==len(temp) and len(result)==3:
                        return []
                temp.clear()
                temp.append(i)
                p = i[0:2]
                c = i[2:4]
                co = i[4:6]
            else:
                if CalcuConfidential([temp[-1]])>CalcuConfidential([i]):
                    if temp[-1][10] != i[10] and not checkonly(temp, i):
                        temp[-1]=i
                        p = i[0:2]
                        c = i[2:4]
                        co = i[4:6]
                elif CalcuConfidential([temp[-1]])==CalcuConfidential([i]):
                    if RankCalcu(temp[-1])>RankCalcu(i) and not checkonly(temp,i):
                        temp[-1] = i
                        p = i[0:2]
                        c = i[2:4]
                        co = i[4:6]
                    else:
                        pass
                else:
                    if len(wait)==0:
                        wait.append(i)
                    elif len(wait)==1:
                        if checkCode(wait[0],i)==0:
                            if RankCalcu(wait[0])<RankCalcu(i) and not checkonly(wait,i):
                                wait.append(i)
                        else:
                            wait[0]=i
                    if len(wait)==2:
                        if wait[0][0:2]!=temp[0][0:2]:
                            pass
                        else:
                            temp[-1]=wait[0]
                            temp.append(wait[1])
                        wait.clear()
                    p = temp[-1][0:2]
                    c = temp[-1][2:4]
                    co = temp[-1][4:6]
        # print(p,c,co)
        # print(result, temp, i,wait, CalcuConfidential(result), CalcuConfidential(temp), CalcuConfidential([i]),CalcuConfidential(wait))
    if CalcuConfidential(result) <= CalcuConfidential(temp):
        if len(result) == 0:
            pass
        elif len(temp) >= 3 and temp[0] != result[0]:
            return temp
        else:
            pass
    else:
        if len(result)<=len(temp):
            result = copy.deepcopy(temp)
        elif len(result)==len(temp) and len(result)==3:
            return []
    return result

# def choosebest(candidate):
#     p='00'
#     c='00'
#     co='00'
#     temp=[]
#     temp1=[]
#     result=[]
#     # if len(words)==1:
#     #     candidate.append(localcode)
#     #     candidate=sorted(candidate,key=cmp_to_key(custom_sort()))
#     chance=1
#     for i in candidate:
#         t = [p, c, co]
#         p = checkPart(p,i[0:2])
#         c = checkPart(c, i[2:4])
#         co = checkPart(co, i[4:6])
#         # print(p,c,co,i)
#         print(result,temp,temp1,CalcuConfidential(result),CalcuConfidential(temp),CalcuConfidential(temp1))
#         if p!=''and c!='' and co!='' and len(temp)==0:
#             temp.append(i)
#         elif p!=''and c!='' and co!='' and len(temp)!=0:
#             o=0
#             for n in temp:
#                 if RankCalcu(i)==RankCalcu(n):
#                     o=1
#                     break
#             if o==0:
#                 temp.append(i)
#         else:
#             if chance == 1:
#                 if checkCode(temp[0], i) == 0:
#                     temp1.append(temp[0])
#                     temp1.append(i)
#                 else:
#                     temp1.append(i)
#                 chance = 0
#                 p = t[0]
#                 c = t[1]
#                 co = t[2]
#             else:
#                 p = checkPart(temp1[-1][0:2], i[0:2])
#                 c = checkPart(temp1[-1][2:4], i[2:4])
#                 co = checkPart(temp1[-1][4:6], i[4:6])
#                 if p != '' and c != '' and co != '':
#                     if CalcuConfidential(result) <= CalcuConfidential(temp):
#                         if len(result)==0:
#                             pass
#                         elif len(temp)>=3 and temp[0]!=result[0]:
#                             return []
#                         else:
#                             pass
#                     else:
#                         result = copy.deepcopy(temp)
#                     temp.clear()
#                     for t in temp1:
#                         temp.append(t)
#                     temp.append(i)
#                     temp1.clear()
#                     chance = 1
#                     continue
#                 if CalcuConfidential(temp1) > CalcuConfidential([i]):
#                     temp1.clear()
#                     temp1.append(i)
#                     p = i[0:2]
#                     c = i[2:4]
#                     co = i[4:6]
#                 else:
#                     p = temp1[-1][0:2]
#                     c = temp1[-1][2:4]
#                     co = temp1[-1][4:6]
#
#                 if CalcuConfidential(result) <= CalcuConfidential(temp):
#                     if len(result) == 0:
#                         pass
#                     elif len(temp) >= 3 and temp[0] != result[0]:
#                         return []
#                     else:
#                         pass
#                 else:
#                     result = copy.deepcopy(temp)
#                 if CalcuConfidential(result) <= CalcuConfidential(temp1):
#                     pass
#                 else:
#                     result = copy.deepcopy(temp1)
#                 # print('result:',result)
#                 temp.clear()
#                 temp.append(temp1[0])
#                 temp1.clear()
#                 chance = 1
#
#     if CalcuConfidential(result) <= CalcuConfidential(temp):
#         if len(result) == 0:
#             pass
#         elif len(temp) >= 3 and temp[0] != result[0]:
#             return []
#         else:
#             pass
#     else:
#         result = copy.deepcopy(temp)
#     if CalcuConfidential(result) <= CalcuConfidential(temp1):
#             pass
#     else:
#         result = copy.deepcopy(temp1)
#     print(result, temp, temp1, CalcuConfidential(result), CalcuConfidential(temp))
#     return result

def readResult(codes):
    code='00000000000'
    for i in codes:
        if checkCode(code,i)==0:
            code=i
    # print('finalcode:',code)
    if code[0:2]!='00':
        p = codeMap[code[0:2]+'0000000']
    else:
        p=''
    if code[2:4] != '00':
        c = codeMap[code[0:4] + '00000']
    else:
        c=''
    if c=='市辖区' or c=='县':
        c=''
    if code[4:6] != '00':
        co = codeMap[code[0:6] + '000']
    else:
        co=''
    if code[6:9] != '000':
        t = codeMap[code[0:9]]
    else:
        t=''
    return p,c,co,t

def judgeResult(result,words):
    l=len(words)
    if l==1 or len(result)==1:
        for i in result:
            for j in words:
                if codeMap[i[0:9]] == j and j!='开发区':
                    return [i]
        return 'notfound'
    # elif l>=2 and l<=4:
    #     hit=0
    #     p,c,co,t=readResult(result)
    #     for i in [p,c,co,t]:
    #         for j in words:
    #             if i == j:
    #                 hit += 1
    #             elif processIndex(i) == j:
    #                 hit+=0.5
    #     # print(hit/l)
    #     if hit/l<0.1:
    #         return 'notfound'
    return result


def parse(s):
    candidate,words = nGramMatch(s)
    l = len(candidate)
    if l == 0:
        return '未识别成功'
    sorted_candidate = sorted(candidate,key=cmp_to_key(custom_sort()))
    # print(sorted_candidate)
    # for i in sorted_candidate:
    #     print(i, ':', codeMap[i[0:9]])
    result = choosebest(sorted_candidate)
    # print(result)
    if len(result)==0:
        return '未识别成功'
    else:
        result=judgeResult(result,words)
    if result=='notfound':
        return '未识别成功'
    p,c,co,_=readResult(result)
    if p+c+co=='':
        return '未识别成功'
    else:
        return p+c+co

def test():
    test=pd.read_csv('test.csv',names=['A'],usecols=[1],skip_blank_lines=True)
    totalnum=0
    succeed=0
    error=0
    t= {}
    for i in test['A']:
        m=parse(i)
        t[str(i)+str(totalnum)]=m
        if m=='未识别成功':
            error+=1
        else:
            succeed+=1
        totalnum+=1
    out=pd.DataFrame.from_dict(t,orient='index')
    out.to_csv('out.csv',encoding='utf-8')
    print('总计处理',totalnum,'条,成功',succeed,'条，失败',error,'条')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:v",
                                   ["help", "infile=", "outfile="])
    except getopt.GetoptError as error:
        print(str(error))
        sys.exit(2)
    infile = None
    output = None
    verbose = False
    for key, value in opts:
        if key == "-v":
            verbose = True
        elif key in ("-h", "--help"):
            print("sysargv.py -i <inputfile> -o <outputfile>")
            print("or sysargv.py --infile <inputfile> --outfile <outputfile>")

        elif key in ("-i", "--infile"):
            infile = value
            init()
            last_time = time.time()
            files=pd.read_csv(infile, names=['A'], usecols=[1], skip_blank_lines=True)
            totalnum = 0
            succeed = 0
            error = 0
            t = {}
            for i in files['A']:
                m = parse(i)
                t[str(i) + str(totalnum)] = m
                if m == '未识别成功':
                    error += 1
                else:
                    succeed += 1
                totalnum += 1
            out = pd.DataFrame.from_dict(t, orient='index')
            out.to_csv('out.csv', encoding='utf-8')
            print('总计处理', totalnum, '条,成功', succeed, '条，失败', error, '条')
            end_time = time.time()
            print('查询时间：%.5f' % (end_time - last_time))

        elif key in ("-o", "--outfile"):
            output = value
            out = pd.DataFrame.from_dict(t, orient='index')
            out.to_csv(value, encoding='utf-8')

    print("inputfile:", infile)
    print("outputfile:", output)

def currentsituation():
    init()
    last_time = time.time()
    test()
    # t = {}
    # m = parse('上海宝山')
    # t['上海宝山'] = m
    # print(t)
    # out = pd.DataFrame.from_dict(t, orient='index')
    # out.to_csv('wenti.csv', encoding='utf-8')

    # print(processIndex('麦子店街道'))
    # print(parse('上海嘉定'))
    # print(parse('贵州省遵义县南白镇南白社区八小区833696'))
    # print(parse('贵州省毕节市层台镇付家沟村上坝组3号827662'))
    # print(parse('福建省台投区洛阳后亭三组后宅88..796832'))
    end_time = time.time()
    print('查询时间：%.5f' % (end_time - last_time))

if __name__ == '__main__':
    currentsituation()