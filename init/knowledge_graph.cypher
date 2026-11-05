// ============================================================
// 中医方剂知识图谱种子数据 (Neo4j 5)
// 节点: Herb / Formula / Syndrome / Symptom / Effect / Meridian / Contraindication
// 关系: CONTAINS / TREATS / MANIFESTS / HAS_EFFECT / ENTERS / CONTRADICTS / INCOMPATIBLE_WITH
// 数据出处以《中国药典》2020 年版、全国中医药行业高等教育规划教材《中药学》《方剂学》、
// 《伤寒论》《金匮要略》《小儿药证直诀》《脾胃论》《医林改错》《太平惠民和剂局方》等为准。
// 幂等：全部使用 MERGE，可重复执行。
// ============================================================

// ---------- 1. 中药 (Herb) ----------
UNWIND [
  {name:'麻黄', pinyin:'mahuang', nature:'温', flavors:['辛','微苦'], meridians:['肺','膀胱'], effects:['发汗解表','宣肺平喘','利水消肿'], toxicity:'无毒', dose:'2~10g', contraindications:['表虚自汗者忌用','高血压者慎用'], source:'《中国药典》2020年版'},
  {name:'桂枝', pinyin:'guizhi', nature:'温', flavors:['辛','甘'], meridians:['心','肺','膀胱'], effects:['发汗解表','温通经脉','助阳化气'], toxicity:'无毒', dose:'3~10g', contraindications:['温热病及阴虚阳盛者慎用'], source:'《中国药典》2020年版'},
  {name:'柴胡', pinyin:'chaihu', nature:'微寒', flavors:['苦','辛'], meridians:['肝','胆'], effects:['疏肝解郁','升举阳气','透表泄热'], toxicity:'无毒', dose:'3~10g', contraindications:['肝阳上亢者慎用'], source:'《中国药典》2020年版'},
  {name:'黄芩', pinyin:'huangqin', nature:'寒', flavors:['苦'], meridians:['肺','胆','脾','大肠','小肠'], effects:['清热燥湿','泻火解毒','止血','清热安胎'], toxicity:'无毒', dose:'3~10g', contraindications:['脾胃虚寒者慎用'], source:'《中国药典》2020年版'},
  {name:'黄连', pinyin:'huanglian', nature:'寒', flavors:['苦'], meridians:['心','脾','胃','肝','胆','大肠'], effects:['清热燥湿','泻火解毒'], toxicity:'无毒', dose:'2~5g', contraindications:['脾胃虚寒者慎用'], source:'《中国药典》2020年版'},
  {name:'大黄', pinyin:'dahuang', nature:'寒', flavors:['苦'], meridians:['脾','胃','大肠','肝','心包'], effects:['泻下攻积','清热泻火','凉血解毒','活血化瘀'], toxicity:'无毒', dose:'3~15g', contraindications:['孕妇及哺乳期慎用','脾胃虚弱者慎用'], source:'《中国药典》2020年版'},
  {name:'人参', pinyin:'renshen', nature:'微温', flavors:['甘','微苦'], meridians:['脾','肺','心','肾'], effects:['大补元气','复脉固脱','补脾益肺','生津养血','安神'], toxicity:'无毒', dose:'3~9g', contraindications:['实证、热证者不宜','反藜芦'], source:'《中国药典》2020年版'},
  {name:'黄芪', pinyin:'huangqi', nature:'微温', flavors:['甘'], meridians:['脾','肺'], effects:['补气升阳','固表止汗','利水消肿','托毒生肌'], toxicity:'无毒', dose:'9~30g', contraindications:['表实邪盛、气滞湿阻者慎用'], source:'《中国药典》2020年版'},
  {name:'白术', pinyin:'baizhu', nature:'温', flavors:['苦','甘'], meridians:['脾','胃'], effects:['健脾益气','燥湿利水','止汗','安胎'], toxicity:'无毒', dose:'6~12g', contraindications:['阴虚燥渴者慎用'], source:'《中国药典》2020年版'},
  {name:'茯苓', pinyin:'fuling', nature:'平', flavors:['甘','淡'], meridians:['心','肺','脾','肾'], effects:['利水渗湿','健脾','宁心安神'], toxicity:'无毒', dose:'10~15g', contraindications:['阴虚而无湿热者慎用'], source:'《中国药典》2020年版'},
  {name:'甘草', pinyin:'gancao', nature:'平', flavors:['甘'], meridians:['心','肺','脾','胃'], effects:['补脾益气','清热解毒','祛痰止咳','缓急止痛','调和诸药'], toxicity:'无毒', dose:'2~10g', contraindications:['反海藻、甘遂、大戟、芫花','湿盛胀满者慎用'], source:'《中国药典》2020年版'},
  {name:'当归', pinyin:'danggui', nature:'温', flavors:['甘','辛'], meridians:['肝','心','脾'], effects:['补血活血','调经止痛','润肠通便'], toxicity:'无毒', dose:'6~12g', contraindications:['湿盛中满、大便溏泻者慎用'], source:'《中国药典》2020年版'},
  {name:'川芎', pinyin:'chuanxiong', nature:'温', flavors:['辛'], meridians:['肝','胆','心包'], effects:['活血行气','祛风止痛'], toxicity:'无毒', dose:'3~10g', contraindications:['阴虚火旺、出血者慎用'], source:'《中国药典》2020年版'},
  {name:'白芍', pinyin:'baishao', nature:'微寒', flavors:['苦','酸'], meridians:['肝','脾'], effects:['养血调经','敛阴止汗','柔肝止痛','平抑肝阳'], toxicity:'无毒', dose:'6~15g', contraindications:['虚寒腹痛腹泻者慎用','反藜芦'], source:'《中国药典》2020年版'},
  {name:'熟地黄', pinyin:'shudihuang', nature:'微温', flavors:['甘'], meridians:['肝','肾'], effects:['补血滋阴','益精填髓'], toxicity:'无毒', dose:'9~15g', contraindications:['脾胃虚弱、气滞痰多腹满便溏者慎用'], source:'《中国药典》2020年版'},
  {name:'生地黄', pinyin:'shengdihuang', nature:'寒', flavors:['甘'], meridians:['心','肝','肾'], effects:['清热凉血','养阴生津'], toxicity:'无毒', dose:'10~15g', contraindications:['脾虚湿滞、腹满便溏者慎用'], source:'《中国药典》2020年版'},
  {name:'枸杞子', pinyin:'gouqizi', nature:'平', flavors:['甘'], meridians:['肝','肾'], effects:['滋补肝肾','益精明目'], toxicity:'无毒', dose:'6~12g', contraindications:['外邪实热、脾虚有湿者慎用'], source:'《中国药典》2020年版'},
  {name:'山药', pinyin:'shanyao', nature:'平', flavors:['甘'], meridians:['脾','肺','肾'], effects:['补脾养胃','生津益肺','补肾涩精'], toxicity:'无毒', dose:'15~30g', contraindications:['湿盛中满或有积滞者慎用'], source:'《中国药典》2020年版'},
  {name:'陈皮', pinyin:'chenpi', nature:'温', flavors:['苦','辛'], meridians:['肺','脾'], effects:['理气健脾','燥湿化痰'], toxicity:'无毒', dose:'3~10g', contraindications:['气虚、阴虚燥咳者慎用'], source:'《中国药典》2020年版'},
  {name:'半夏', pinyin:'banxia', nature:'温', flavors:['辛'], meridians:['脾','胃','肺'], effects:['燥湿化痰','降逆止呕','消痞散结'], toxicity:'有毒', dose:'3~9g', contraindications:['阴虚燥咳、津伤口渴者忌用','反乌头'], source:'《中国药典》2020年版'},
  {name:'生姜', pinyin:'shengjiang', nature:'微温', flavors:['辛'], meridians:['肺','脾','胃'], effects:['解表散寒','温中止呕','化痰止咳'], toxicity:'无毒', dose:'3~10g', contraindications:['阴虚内热者慎用'], source:'《中国药典》2020年版'},
  {name:'大枣', pinyin:'dazao', nature:'温', flavors:['甘'], meridians:['脾','胃','心'], effects:['补中益气','养血安神'], toxicity:'无毒', dose:'6~15g', contraindications:['湿盛脘腹胀满者慎用'], source:'《中国药典》2020年版'},
  {name:'薄荷', pinyin:'bohe', nature:'凉', flavors:['辛'], meridians:['肺','肝'], effects:['疏散风热','清利头目','疏肝行气'], toxicity:'无毒', dose:'3~6g', contraindications:['体虚多汗者慎用'], source:'《中国药典》2020年版'},
  {name:'葛根', pinyin:'gegen', nature:'凉', flavors:['甘','辛'], meridians:['脾','胃','肺'], effects:['解肌退热','生津止渴','升阳止泻','透疹'], toxicity:'无毒', dose:'10~15g', contraindications:['胃寒者慎用'], source:'《中国药典》2020年版'},
  {name:'丹参', pinyin:'danshen', nature:'微寒', flavors:['苦'], meridians:['心','肝'], effects:['活血祛瘀','通经止痛','清心除烦','凉血消痈'], toxicity:'无毒', dose:'10~15g', contraindications:['反藜芦','无瘀血者慎用'], source:'《中国药典》2020年版'},
  {name:'郁金', pinyin:'yujin', nature:'寒', flavors:['辛','苦'], meridians:['肝','心','肺'], effects:['活血止痛','行气解郁','清心凉血','利胆退黄'], toxicity:'无毒', dose:'3~10g', contraindications:['畏丁香','阴虚失血者慎用'], source:'《中国药典》2020年版'},
  {name:'酸枣仁', pinyin:'suanzaoren', nature:'平', flavors:['甘','酸'], meridians:['肝','胆','心'], effects:['养心补肝','宁心安神','敛汗生津'], toxicity:'无毒', dose:'10~15g', contraindications:['有实邪者慎用'], source:'《中国药典》2020年版'},
  {name:'牡蛎', pinyin:'muli', nature:'微寒', flavors:['咸'], meridians:['肝','胆','肾'], effects:['重镇安神','平肝潜阳','软坚散结','收敛固涩'], toxicity:'无毒', dose:'9~30g', contraindications:['虚而有寒者慎用'], source:'《中国药典》2020年版'},
  {name:'龙骨', pinyin:'longgu', nature:'平', flavors:['甘','涩'], meridians:['心','肝','肾'], effects:['镇惊安神','平肝潜阳','收敛固涩'], toxicity:'无毒', dose:'15~30g', contraindications:['有湿热积滞者慎用'], source:'《中国药典》2020年版'},
  {name:'泽泻', pinyin:'zexie', nature:'寒', flavors:['甘'], meridians:['肾','膀胱'], effects:['利水渗湿','泄热','化浊降脂'], toxicity:'无毒', dose:'6~10g', contraindications:['肾虚精滑无湿热者慎用'], source:'《中国药典》2020年版'},
  {name:'麦冬', pinyin:'maidong', nature:'微寒', flavors:['甘','微苦'], meridians:['心','肺','胃'], effects:['养阴生津','润肺清心'], toxicity:'无毒', dose:'6~12g', contraindications:['脾胃虚寒泄泻、风寒咳嗽者慎用'], source:'《中国药典》2020年版'},
  {name:'党参', pinyin:'dangshen', nature:'平', flavors:['甘'], meridians:['脾','肺'], effects:['补中益气','健脾益肺','养血生津'], toxicity:'无毒', dose:'9~30g', contraindications:['实证、热证者慎用'], source:'《中国药典》2020年版'},
  {name:'附子', pinyin:'fuzi', nature:'大热', flavors:['辛','甘'], meridians:['心','肾','脾'], effects:['回阳救逆','补火助阳','散寒止痛'], toxicity:'有毒', dose:'3~15g', contraindications:['阴虚阳亢者忌用','孕妇慎用','反半夏、瓜蒌、贝母、白蔹、白及'], source:'《中国药典》2020年版'},
  {name:'干姜', pinyin:'ganjiang', nature:'热', flavors:['辛'], meridians:['脾','胃','心','肺'], effects:['温中散寒','回阳通脉','温肺化饮'], toxicity:'无毒', dose:'3~10g', contraindications:['阴虚内热、血热妄行者慎用'], source:'《中国药典》2020年版'},
  {name:'海藻', pinyin:'haizao', nature:'寒', flavors:['苦','咸'], meridians:['肝','胃','肾'], effects:['软坚散结','消痰利水'], toxicity:'无毒', dose:'6~12g', contraindications:['反甘草','脾虚便溏者慎用'], source:'《中国药典》2020年版'},
  {name:'甘遂', pinyin:'gansui', nature:'寒', flavors:['苦'], meridians:['肺','肾','大肠'], effects:['泻水逐饮','消肿散结'], toxicity:'有毒', dose:'0.5~1.5g', contraindications:['反甘草','孕妇忌用'], source:'《中国药典》2020年版'},
  {name:'大戟', pinyin:'daji', nature:'寒', flavors:['苦'], meridians:['肺','脾','肾'], effects:['泻水逐饮','消肿散结'], toxicity:'有毒', dose:'1.5~3g', contraindications:['反甘草','孕妇忌用'], source:'《中国药典》2020年版'},
  {name:'芫花', pinyin:'yuanhua', nature:'温', flavors:['苦','辛'], meridians:['肺','脾','肾'], effects:['泻水逐饮','祛痰止咳','杀虫疗疮'], toxicity:'有毒', dose:'1.5~3g', contraindications:['反甘草','孕妇忌用'], source:'《中国药典》2020年版'},
  {name:'川贝母', pinyin:'chuanbeimu', nature:'微寒', flavors:['苦','甘'], meridians:['肺','心'], effects:['清热化痰','润肺止咳','散结消肿'], toxicity:'无毒', dose:'3~10g', contraindications:['反乌头','脾胃虚寒者慎用'], source:'《中国药典》2020年版'},
  {name:'瓜蒌', pinyin:'gualou', nature:'寒', flavors:['甘','微苦'], meridians:['肺','胃','大肠'], effects:['清热涤痰','宽胸散结','润燥滑肠'], toxicity:'无毒', dose:'9~15g', contraindications:['反乌头','脾虚便溏者慎用'], source:'《中国药典》2020年版'},
  {name:'丁香', pinyin:'dingxiang', nature:'温', flavors:['辛'], meridians:['脾','胃','肺','肾'], effects:['温中降逆','补肾助阳'], toxicity:'无毒', dose:'1~3g', contraindications:['畏郁金','热证及阴虚内热者慎用'], source:'《中国药典》2020年版'},
  {name:'五灵脂', pinyin:'wulingzhi', nature:'温', flavors:['苦','咸','甘'], meridians:['肝'], effects:['活血止痛','化瘀止血'], toxicity:'无毒', dose:'3~10g', contraindications:['畏人参','孕妇慎用'], source:'《中国药典》2020年版'},
  {name:'杏仁', pinyin:'xingren', nature:'微温', flavors:['苦'], meridians:['肺','大肠'], effects:['降气止咳平喘','润肠通便'], toxicity:'小毒', dose:'3~10g', contraindications:['婴儿慎用','阴虚咳嗽者慎用'], source:'《中国药典》2020年版'},
  {name:'山茱萸', pinyin:'shanzhuyu', nature:'微温', flavors:['酸','涩'], meridians:['肝','肾'], effects:['补益肝肾','收涩固脱'], toxicity:'无毒', dose:'6~12g', contraindications:['命门火炽、湿热者慎用'], source:'《中国药典》2020年版'},
  {name:'牡丹皮', pinyin:'mudanpi', nature:'微寒', flavors:['苦','辛'], meridians:['心','肝','肾'], effects:['清热凉血','活血化瘀'], toxicity:'无毒', dose:'6~12g', contraindications:['血虚有寒、月经过多者慎用'], source:'《中国药典》2020年版'},
  {name:'龙眼肉', pinyin:'longyanrou', nature:'温', flavors:['甘'], meridians:['心','脾'], effects:['补益心脾','养血安神'], toxicity:'无毒', dose:'9~15g', contraindications:['湿盛中满及痰火者慎用'], source:'《中国药典》2020年版'},
  {name:'远志', pinyin:'yuanzhi', nature:'温', flavors:['苦','辛'], meridians:['心','肾','肺'], effects:['安神益智','交通心肾','祛痰开窍'], toxicity:'无毒', dose:'3~10g', contraindications:['实热者慎用'], source:'《中国药典》2020年版'},
  {name:'木香', pinyin:'muxiang', nature:'温', flavors:['辛','苦'], meridians:['脾','胃','大肠','三焦','胆'], effects:['行气止痛','健脾消食'], toxicity:'无毒', dose:'3~6g', contraindications:['阴虚津亏者慎用'], source:'《中国药典》2020年版'},
  {name:'升麻', pinyin:'shengma', nature:'微寒', flavors:['辛','甘'], meridians:['肺','脾','胃','大肠'], effects:['升举阳气','发表透疹','清热解毒'], toxicity:'无毒', dose:'3~10g', contraindications:['麻疹已透、阴虚火旺者慎用'], source:'《中国药典》2020年版'},
  {name:'桃仁', pinyin:'taoren', nature:'平', flavors:['苦','甘'], meridians:['心','肝','大肠'], effects:['活血祛瘀','润肠通便','止咳平喘'], toxicity:'小毒', dose:'5~10g', contraindications:['孕妇慎用'], source:'《中国药典》2020年版'},
  {name:'红花', pinyin:'honghua', nature:'温', flavors:['辛'], meridians:['心','肝'], effects:['活血通经','散瘀止痛'], toxicity:'无毒', dose:'3~10g', contraindications:['孕妇慎用','有出血倾向者慎用'], source:'《中国药典》2020年版'},
  {name:'赤芍', pinyin:'chishao', nature:'微寒', flavors:['苦'], meridians:['肝'], effects:['清热凉血','散瘀止痛'], toxicity:'无毒', dose:'6~12g', contraindications:['血寒经闭者不宜'], source:'《中国药典》2020年版'},
  {name:'牛膝', pinyin:'niuxi', nature:'平', flavors:['苦','甘','酸'], meridians:['肝','肾'], effects:['逐瘀通经','补肝肾','强筋骨','引血下行'], toxicity:'无毒', dose:'5~12g', contraindications:['孕妇慎用'], source:'《中国药典》2020年版'},
  {name:'桔梗', pinyin:'jiegeng', nature:'平', flavors:['苦','辛'], meridians:['肺'], effects:['宣肺','利咽','祛痰','排脓'], toxicity:'无毒', dose:'3~10g', contraindications:['阴虚久咳者慎用'], source:'《中国药典》2020年版'},
  {name:'枳壳', pinyin:'zhike', nature:'微寒', flavors:['苦','辛','酸'], meridians:['脾','胃'], effects:['理气宽中','行滞消胀'], toxicity:'无毒', dose:'3~10g', contraindications:['孕妇慎用'], source:'《中国药典》2020年版'},
  {name:'薏苡仁', pinyin:'yiyiren', nature:'凉', flavors:['甘','淡'], meridians:['脾','胃','肺'], effects:['利水渗湿','健脾止泻','除痹排脓'], toxicity:'无毒', dose:'9~30g', contraindications:['孕妇慎用'], source:'《中国药典》2020年版'},
  {name:'砂仁', pinyin:'sharen', nature:'温', flavors:['辛'], meridians:['脾','胃','肾'], effects:['化湿开胃','温脾止泻','理气安胎'], toxicity:'无毒', dose:'3~6g', contraindications:['阴虚血燥者慎用'], source:'《中国药典》2020年版'},
  {name:'龙胆', pinyin:'longdan', nature:'寒', flavors:['苦'], meridians:['肝','胆'], effects:['清热燥湿','泻肝胆火'], toxicity:'无毒', dose:'3~6g', contraindications:['脾胃虚寒者慎用'], source:'《中国药典》2020年版'},
  {name:'栀子', pinyin:'zhizi', nature:'寒', flavors:['苦'], meridians:['心','肺','三焦'], effects:['泻火除烦','清热利湿','凉血解毒'], toxicity:'无毒', dose:'6~10g', contraindications:['脾虚便溏者慎用'], source:'《中国药典》2020年版'},
  {name:'车前子', pinyin:'cheqianzi', nature:'寒', flavors:['甘'], meridians:['肝','肾','肺','小肠'], effects:['清热利尿','渗湿止泻','明目','祛痰'], toxicity:'无毒', dose:'9~15g', contraindications:['肾虚滑精者慎用'], source:'《中国药典》2020年版'},
  {name:'木通', pinyin:'mutong', nature:'寒', flavors:['苦'], meridians:['心','小肠','膀胱'], effects:['利尿通淋','清心除烦','通经下乳'], toxicity:'无毒', dose:'3~6g', contraindications:['孕妇慎用','肾功能不全者慎用'], source:'《中国药典》2020年版'}
] AS row
MERGE (h:Herb {name: row.name})
SET h.pinyin = row.pinyin, h.nature = row.nature, h.flavors = row.flavors,
    h.meridians = row.meridians, h.effects = row.effects, h.toxicity = row.toxicity,
    h.daily_dose_range = row.dose, h.contraindications = row.contraindications,
    h.source = row.source, h.updated_at = datetime()
WITH row
UNWIND row.meridians AS m
MATCH (h:Herb {name: row.name})
MERGE (mer:Meridian {name: m})
MERGE (h)-[:ENTERS]->(mer)
WITH row
UNWIND row.effects AS e
MATCH (h:Herb {name: row.name})
MERGE (eff:Effect {name: e})
MERGE (h)-[:HAS_EFFECT]->(eff);

// ---------- 2. 症状 (Symptom) ----------
UNWIND [
  {name:'恶寒', location:'全身', nature:'寒', aliases:['怕冷','畏寒']},
  {name:'发热', location:'全身', nature:'热', aliases:['发烧']},
  {name:'头痛', location:'头部', nature:'痛', aliases:[]},
  {name:'无汗', location:'皮肤', nature:'表证', aliases:[]},
  {name:'自汗', location:'皮肤', nature:'气虚', aliases:[]},
  {name:'盗汗', location:'皮肤', nature:'阴虚', aliases:[]},
  {name:'鼻塞', location:'鼻', nature:'外感', aliases:[]},
  {name:'流清涕', location:'鼻', nature:'风寒', aliases:[]},
  {name:'咳嗽', location:'肺', nature:'肺失宣降', aliases:[]},
  {name:'咳痰', location:'肺', nature:'痰', aliases:['咯痰']},
  {name:'咽喉痛', location:'咽喉', nature:'热', aliases:['咽痛']},
  {name:'口苦', location:'口', nature:'热', aliases:[]},
  {name:'口干', location:'口', nature:'津亏', aliases:['口燥']},
  {name:'口渴', location:'口', nature:'津伤', aliases:['口干欲饮']},
  {name:'食欲不振', location:'脾胃', nature:'气虚', aliases:['纳呆','食少']},
  {name:'腹胀', location:'腹', nature:'气滞', aliases:['脘腹胀满']},
  {name:'便溏', location:'大肠', nature:'脾虚湿盛', aliases:['大便稀']},
  {name:'便秘', location:'大肠', nature:'腑气不通', aliases:['大便干结']},
  {name:'尿黄', location:'膀胱', nature:'热', aliases:['小便黄赤']},
  {name:'尿频', location:'膀胱', nature:'肾虚', aliases:['小便频数']},
  {name:'夜尿多', location:'膀胱', nature:'肾阳虚', aliases:['夜尿频']},
  {name:'失眠', location:'心', nature:'心神不安', aliases:['不寐','入睡困难']},
  {name:'多梦', location:'心', nature:'心神不宁', aliases:[]},
  {name:'心悸', location:'心', nature:'心失所养', aliases:['心慌']},
  {name:'健忘', location:'心', nature:'心脾两虚', aliases:[]},
  {name:'神疲乏力', location:'全身', nature:'气虚', aliases:['乏力','疲倦']},
  {name:'头晕', location:'头部', nature:'虚', aliases:['眩晕']},
  {name:'面色萎黄', location:'面', nature:'血虚', aliases:['面黄']},
  {name:'面色苍白', location:'面', nature:'血虚', aliases:['面白']},
  {name:'五心烦热', location:'全身', nature:'阴虚', aliases:['手足心热','潮热']},
  {name:'潮热', location:'全身', nature:'阴虚', aliases:[]},
  {name:'腰膝酸软', location:'腰膝', nature:'肾虚', aliases:['腰酸']},
  {name:'畏寒肢冷', location:'四肢', nature:'阳虚', aliases:['四肢不温']},
  {name:'胸胁胀痛', location:'胸胁', nature:'肝郁气滞', aliases:['胁痛']},
  {name:'善太息', location:'胸', nature:'肝气郁结', aliases:['叹气']},
  {name:'情志抑郁', location:'神志', nature:'肝郁', aliases:['情绪低落']},
  {name:'刺痛', location:'全身', nature:'血瘀', aliases:['固定刺痛']},
  {name:'月经不调', location:'妇科', nature:'气血失调', aliases:['月经紊乱']},
  {name:'肢体困重', location:'肢体', nature:'湿', aliases:['身重']},
  {name:'痰多', location:'肺', nature:'痰湿', aliases:['咳痰量多']},
  {name:'面色晦暗', location:'面', nature:'血瘀', aliases:['面色暗']},
  {name:'手足心热', location:'手足', nature:'阴虚', aliases:[]},
  {name:'口淡', location:'口', nature:'脾虚', aliases:[]},
  {name:'大便干结', location:'大肠', nature:'燥热', aliases:['便秘']},
  {name:'夜不能寐', location:'心', nature:'虚烦', aliases:['失眠']}
] AS row
MERGE (s:Symptom {name: row.name})
SET s.location = row.location, s.nature = row.nature, s.aliases = row.aliases,
    s.source = '《中医诊断学》教材', s.updated_at = datetime();

// ---------- 3. 证型 (Syndrome) ----------
UNWIND [
  {name:'风寒束表证', definition:'外感风寒之邪，卫阳被遏，腠理闭塞，肺气失宣所致的表实寒证。', main:['恶寒','发热','无汗','头痛'], acc:['鼻塞','流清涕','咳嗽','脉浮紧'], tongue:'舌苔薄白', pulse:'脉浮紧', tp:'辛温解表，宣肺散寒', formulas:['麻黄汤','桂枝汤'], source:'《伤寒论》'},
  {name:'肝郁气滞证', definition:'肝失疏泄，气机郁滞，以情志抑郁、胸胁胀痛等为主要表现的证候。', main:['情志抑郁','胸胁胀痛','善太息'], acc:['月经不调','腹胀','脉弦'], tongue:'舌苔薄白', pulse:'脉弦', tp:'疏肝解郁，理气健脾', formulas:['逍遥散'], source:'《中医诊断学》教材'},
  {name:'脾胃气虚证', definition:'脾气不足，失于健运，以食少、腹胀、便溏、神疲乏力等为主要表现。', main:['食欲不振','腹胀','便溏','神疲乏力'], acc:['面色萎黄','气短','脉虚弱'], tongue:'舌淡苔白', pulse:'脉虚弱', tp:'健脾益气，渗湿和胃', formulas:['四君子汤','参苓白术散','补中益气汤'], source:'《中医诊断学》教材'},
  {name:'气血两虚证', definition:'气虚与血虚并见，脏腑经络失于濡养。', main:['神疲乏力','面色萎黄','头晕','心悸'], acc:['失眠','月经不调','脉细弱'], tongue:'舌淡', pulse:'脉细弱', tp:'益气补血', formulas:['八珍汤','归脾汤'], source:'《中医诊断学》教材'},
  {name:'肾阴虚证', definition:'肾阴亏损，失于滋养，虚热内生，以腰膝酸软、潮热盗汗为主。', main:['腰膝酸软','五心烦热','潮热','盗汗'], acc:['眩晕','耳鸣','失眠','脉细数'], tongue:'舌红少苔', pulse:'脉细数', tp:'滋补肾阴', formulas:['六味地黄丸'], source:'《中医诊断学》教材'},
  {name:'心脾两虚证', definition:'心脾气血两虚，心神失养，脾失健运。', main:['心悸','健忘','失眠','食欲不振'], acc:['面色萎黄','神疲乏力','便溏','脉细弱'], tongue:'舌淡', pulse:'脉细弱', tp:'益气补血，健脾养心', formulas:['归脾汤'], source:'《济生方》'},
  {name:'痰湿内阻证', definition:'脾失健运，痰湿内生，停聚中焦。', main:['痰多','肢体困重','胸脘痞闷'], acc:['食欲不振','便溏','头晕','脉滑'], tongue:'舌苔白腻', pulse:'脉滑', tp:'燥湿化痰，理气和中', formulas:['二陈汤'], source:'《中医诊断学》教材'},
  {name:'气滞血瘀证', definition:'气机郁滞而致血行瘀阻。', main:['刺痛','面色晦暗','胸胁胀痛'], acc:['月经不调','舌有瘀斑','脉涩'], tongue:'舌紫暗或有瘀斑', pulse:'脉涩', tp:'活血化瘀，行气止痛', formulas:['血府逐瘀汤'], source:'《医林改错》'},
  {name:'肝胆湿热证', definition:'湿热内蕴肝胆，疏泄失常。', main:['口苦','胁痛','尿黄'], acc:['目赤','身黄','脉弦数'], tongue:'舌红苔黄腻', pulse:'脉弦数', tp:'清泻肝胆实火，清利肝胆湿热', formulas:['龙胆泻肝汤'], source:'《中医诊断学》教材'},
  {name:'肾阳虚证', definition:'肾阳亏虚，温煦失职，气化无权。', main:['畏寒肢冷','腰膝酸软','夜尿多'], acc:['神疲乏力','面色苍白','脉沉迟'], tongue:'舌淡胖', pulse:'脉沉迟', tp:'温补肾阳', formulas:['四逆汤'], source:'《中医诊断学》教材'}
] AS row
MERGE (s:Syndrome {name: row.name})
SET s.definition = row.definition, s.main_symptoms = row.main, s.accompanying_symptoms = row.acc,
    s.tongue = row.tongue, s.pulse = row.pulse, s.treatment_principle = row.tp,
    s.formulas = row.formulas, s.source = row.source, s.updated_at = datetime()
WITH row
UNWIND row.main AS sm
MATCH (sy:Syndrome {name: row.name}), (sym:Symptom {name: sm})
MERGE (sy)-[:MANIFESTS {is_main: true}]->(sym)
WITH row
UNWIND row.acc AS sa
MATCH (sy:Syndrome {name: row.name}), (sym:Symptom {name: sa})
MERGE (sy)-[:MANIFESTS {is_main: false}]->(sym);

// ---------- 4. 方剂 (Formula) ----------
UNWIND [
  {name:'麻黄汤', aliases:['麻黄汤'], source:'《伤寒论》', composition:'麻黄、桂枝、杏仁、甘草', effects:['发汗解表','宣肺平喘'], indications:['风寒束表证'], usage:'水煎温服，覆被取微汗，禁大汗', dosage_note:'体虚外感者不宜', contraindications:['表虚自汗者忌用'], herbs:[['麻黄','9g'],['桂枝','6g'],['杏仁','9g'],['甘草','3g']], treits:['风寒束表证']},
  {name:'桂枝汤', aliases:['阳旦汤'], source:'《伤寒论》', composition:'桂枝、白芍、生姜、大枣、甘草', effects:['解肌发表','调和营卫'], indications:['风寒束表证(表虚)'], usage:'水煎温服，服后啜热稀粥助药力', dosage_note:'', contraindications:['表实无汗者慎用'], herbs:[['桂枝','9g'],['白芍','9g'],['生姜','9g'],['大枣','12g'],['甘草','6g']], treits:['风寒束表证']},
  {name:'小柴胡汤', aliases:['小柴胡汤'], source:'《伤寒论》', composition:'柴胡、黄芩、人参、半夏、生姜、大枣、甘草', effects:['和解少阳','扶正祛邪'], indications:['少阳病'], usage:'水煎温服', dosage_note:'', contraindications:['阴虚血少者慎用'], herbs:[['柴胡','12g'],['黄芩','9g'],['人参','6g'],['半夏','9g'],['生姜','9g'],['大枣','12g'],['甘草','6g']], treits:['肝郁气滞证']},
  {name:'四君子汤', aliases:['四君子汤'], source:'《太平惠民和剂局方》', composition:'人参、白术、茯苓、甘草', effects:['益气健脾'], indications:['脾胃气虚证'], usage:'水煎服', dosage_note:'', contraindications:['脾胃气虚有热者慎用'], herbs:[['人参','9g'],['白术','9g'],['茯苓','9g'],['甘草','6g']], treits:['脾胃气虚证']},
  {name:'四物汤', aliases:['四物汤'], source:'《太平惠民和剂局方》', composition:'当归、川芎、白芍、熟地黄', effects:['补血调血'], indications:['血虚证'], usage:'水煎服', dosage_note:'', contraindications:['湿盛中满者慎用'], herbs:[['当归','9g'],['川芎','6g'],['白芍','9g'],['熟地黄','12g']], treits:['气血两虚证']},
  {name:'八珍汤', aliases:['八珍汤'], source:'《太平惠民和剂局方》', composition:'人参、白术、茯苓、甘草、当归、川芎、白芍、熟地黄', effects:['益气补血'], indications:['气血两虚证'], usage:'水煎服', dosage_note:'', contraindications:['外感未清者慎用'], herbs:[['人参','9g'],['白术','9g'],['茯苓','9g'],['甘草','6g'],['当归','9g'],['川芎','6g'],['白芍','9g'],['熟地黄','12g']], treits:['气血两虚证']},
  {name:'六味地黄丸', aliases:['六味丸'], source:'《小儿药证直诀》', composition:'熟地黄、山茱萸、山药、泽泻、牡丹皮、茯苓', effects:['滋阴补肾'], indications:['肾阴虚证'], usage:'口服丸剂或作汤剂', dosage_note:'', contraindications:['脾虚便溏者慎用'], herbs:[['熟地黄','24g'],['山茱萸','12g'],['山药','12g'],['泽泻','9g'],['牡丹皮','9g'],['茯苓','9g']], treits:['肾阴虚证']},
  {name:'归脾汤', aliases:['归脾汤'], source:'《济生方》', composition:'人参、黄芪、白术、茯苓、当归、酸枣仁、龙眼肉、远志、木香、甘草', effects:['益气补血','健脾养心'], indications:['心脾两虚证'], usage:'水煎服', dosage_note:'', contraindications:['阴虚火旺者慎用'], herbs:[['人参','9g'],['黄芪','12g'],['白术','9g'],['茯苓','9g'],['当归','9g'],['酸枣仁','12g'],['龙眼肉','12g'],['远志','6g'],['木香','6g'],['甘草','6g']], treits:['心脾两虚证','气血两虚证']},
  {name:'四逆汤', aliases:['四逆汤'], source:'《伤寒论》', composition:'附子、干姜、甘草', effects:['回阳救逆'], indications:['阳虚证(少阴阳衰)'], usage:'水煎温服', dosage_note:'附子须先煎', contraindications:['真热假寒者忌用'], herbs:[['附子','9g'],['干姜','6g'],['甘草','6g']], treits:['肾阳虚证']},
  {name:'补中益气汤', aliases:['补中益气汤'], source:'《脾胃论》', composition:'黄芪、人参、白术、当归、陈皮、升麻、柴胡、甘草', effects:['补中益气','升阳举陷'], indications:['脾胃气虚证(中气下陷)'], usage:'水煎服', dosage_note:'', contraindications:['阴虚发热者慎用'], herbs:[['黄芪','15g'],['人参','9g'],['白术','9g'],['当归','9g'],['陈皮','6g'],['升麻','6g'],['柴胡','6g'],['甘草','6g']], treits:['脾胃气虚证']},
  {name:'逍遥散', aliases:['逍遥散'], source:'《太平惠民和剂局方》', composition:'柴胡、当归、白芍、白术、茯苓、薄荷、生姜、甘草', effects:['疏肝解郁','养血健脾'], indications:['肝郁气滞证(肝郁血虚脾弱)'], usage:'水煎服', dosage_note:'', contraindications:['肝阳上亢者慎用'], herbs:[['柴胡','9g'],['当归','9g'],['白芍','9g'],['白术','9g'],['茯苓','9g'],['薄荷','6g'],['生姜','9g'],['甘草','6g']], treits:['肝郁气滞证']},
  {name:'血府逐瘀汤', aliases:['血府逐瘀汤'], source:'《医林改错》', composition:'桃仁、红花、当归、川芎、赤芍、生地黄、牛膝、柴胡、桔梗、枳壳、甘草', effects:['活血化瘀','行气止痛'], indications:['气滞血瘀证(胸中血瘀)'], usage:'水煎服', dosage_note:'', contraindications:['孕妇慎用'], herbs:[['桃仁','12g'],['红花','9g'],['当归','9g'],['川芎','6g'],['赤芍','9g'],['生地黄','9g'],['牛膝','9g'],['柴胡','6g'],['桔梗','6g'],['枳壳','6g'],['甘草','6g']], treits:['气滞血瘀证']},
  {name:'二陈汤', aliases:['二陈汤'], source:'《太平惠民和剂局方》', composition:'半夏、陈皮、茯苓、甘草', effects:['燥湿化痰','理气和中'], indications:['痰湿内阻证(湿痰)'], usage:'水煎，加生姜、乌梅少许', dosage_note:'', contraindications:['阴虚燥咳者忌用'], herbs:[['半夏','9g'],['陈皮','6g'],['茯苓','9g'],['甘草','6g']], treits:['痰湿内阻证']},
  {name:'龙胆泻肝汤', aliases:['龙胆泻肝汤'], source:'《医方集解》', composition:'龙胆、黄芩、栀子、泽泻、木通、车前子、当归、生地黄、柴胡、甘草', effects:['清泻肝胆实火','清利肝胆湿热'], indications:['肝胆湿热证'], usage:'水煎服', dosage_note:'', contraindications:['脾胃虚寒者慎用'], herbs:[['龙胆','6g'],['黄芩','9g'],['栀子','9g'],['泽泻','12g'],['木通','6g'],['车前子','9g'],['当归','9g'],['生地黄','12g'],['柴胡','6g'],['甘草','6g']], treits:['肝胆湿热证']},
  {name:'参苓白术散', aliases:['参苓白术散'], source:'《太平惠民和剂局方》', composition:'人参、白术、茯苓、山药、薏苡仁、砂仁、桔梗、甘草', effects:['益气健脾','渗湿止泻'], indications:['脾胃气虚证(脾虚湿盛)'], usage:'水煎服', dosage_note:'', contraindications:['湿热内蕴者慎用'], herbs:[['人参','9g'],['白术','9g'],['茯苓','9g'],['山药','12g'],['薏苡仁','12g'],['砂仁','6g'],['桔梗','6g'],['甘草','6g']], treits:['脾胃气虚证']}
] AS row
MERGE (f:Formula {name: row.name})
SET f.aliases = row.aliases, f.source = row.source, f.composition = row.composition,
    f.effects = row.effects, f.indications = row.indications, f.usage = row.usage,
    f.dosage_note = row.dosage_note, f.contraindications = row.contraindications,
    f.updated_at = datetime()
WITH row
UNWIND row.herbs AS hc
MATCH (f:Formula {name: row.name}), (h:Herb {name: hc[0]})
MERGE (f)-[:CONTAINS {dosage: hc[1]}]->(h)
WITH row
UNWIND row.treits AS tr
MATCH (f:Formula {name: row.name}), (sy:Syndrome {name: tr})
MERGE (f)-[:TREATS]->(sy);

// ---------- 5. 禁忌节点与配伍禁忌 (十八反 / 十九畏) ----------
UNWIND [
  {name:'孕妇慎用', category:'人群'},
  {name:'表虚自汗者忌用', category:'证候'},
  {name:'反甘草', category:'配伍'},
  {name:'反乌头', category:'配伍'},
  {name:'畏郁金', category:'配伍'},
  {name:'畏人参', category:'配伍'}
] AS row
MERGE (c:Contraindication {name: row.name})
SET c.category = row.category, c.source = '《中国药典》2020年版', c.updated_at = datetime();

// 代表方中药与禁忌的对应关系
MATCH (h:Herb {name:'麻黄'}), (c:Contraindication {name:'表虚自汗者忌用'}) MERGE (h)-[:CONTRADICTS]->(c);
MATCH (h:Herb {name:'大黄'}), (c:Contraindication {name:'孕妇慎用'}) MERGE (h)-[:CONTRADICTS]->(c);
MATCH (h:Herb {name:'甘草'}), (c:Contraindication {name:'反甘草'}) MERGE (h)-[:CONTRADICTS]->(c);
MATCH (h:Herb {name:'半夏'}), (c:Contraindication {name:'反乌头'}) MERGE (h)-[:CONTRADICTS]->(c);
MATCH (h:Herb {name:'丁香'}), (c:Contraindication {name:'畏郁金'}) MERGE (h)-[:CONTRADICTS]->(c);
MATCH (h:Herb {name:'五灵脂'}), (c:Contraindication {name:'畏人参'}) MERGE (h)-[:CONTRADICTS]->(c);

// 十八反 / 十九畏 (双向记录，附 rule)
UNWIND [
  ['甘草','海藻','十八反：甘草反海藻'],
  ['甘草','甘遂','十八反：甘草反甘遂'],
  ['甘草','大戟','十八反：甘草反大戟'],
  ['甘草','芫花','十八反：甘草反芫花'],
  ['附子','半夏','十八反：乌头(附子)反半夏'],
  ['附子','川贝母','十八反：乌头(附子)反贝母'],
  ['附子','瓜蒌','十八反：乌头(附子)反瓜蒌'],
  ['人参','五灵脂','十九畏：人参畏五灵脂'],
  ['丁香','郁金','十九畏：丁香畏郁金']
] AS r
MATCH (a:Herb {name: r[0]}), (b:Herb {name: r[1]})
MERGE (a)-[:INCOMPATIBLE_WITH {rule: r[2]}]->(b)
MERGE (b)-[:INCOMPATIBLE_WITH {rule: r[2]}]->(a);

RETURN 'knowledge graph seeded' AS status;