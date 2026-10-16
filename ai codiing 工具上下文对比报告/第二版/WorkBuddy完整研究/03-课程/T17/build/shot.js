const { chromium } = require("playwright-core");
const path=require("path"); const {pathToFileURL}=require("url");
const FILE=pathToFileURL(path.resolve(__dirname,"..","交互教材.html")).href;
// [名称, 单元, 宽度, 选项]；选项：colorScheme（深色模式）、action（截图前的页面动作）
const shots=[
 ["1440-b1-预算演算器","b1",1440],
 ["390-b1-逐步演算-完整","b1",390,{action:async p=>{await p.click("#calcRun")}}],
 ["390-b2-裁剪器","b2",390],
 ["320-b3-压缩四幕","b3",320],
 ["1440-b4-状态机","b4",1440],
 ["390-b5-三问卡","b5",390],
 ["1440-b6-账单器","b6",1440],
 ["768-dark-b6-账单器","b6",768,{colorScheme:"dark"}],
 ["768-b7-时间线","b7",768],
 ["320-appendix-表格卡片","appendix",320]
];
(async()=>{
const b=await chromium.launch({executablePath:"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",headless:true});
for(const [name,unit,w,optRaw] of shots){
  const opt=optRaw||{};
  const ctxOpts={viewport:{width:w,height:1000}};
  if(opt.colorScheme)ctxOpts.colorScheme=opt.colorScheme;
  const ctx=await b.newContext(ctxOpts);
  const p=await ctx.newPage();
  await p.goto(FILE,{waitUntil:"load"});
  await p.evaluate(id=>{document.querySelectorAll(".unit").forEach(e=>e.classList.remove("active"));document.getElementById(id).classList.add("active")},unit);
  if(opt.action)await opt.action(p);
  await p.waitForTimeout(150);
  await p.screenshot({path:path.join(__dirname,"screenshots",name+".png"),fullPage:true});
  await ctx.close();
  console.log("shot:",name);
}
await b.close();
})();
