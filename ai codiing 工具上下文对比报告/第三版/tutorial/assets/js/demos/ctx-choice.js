/* 第 6 章 · 情景练习：给定情景，选一个动作，看它对下一次请求做了什么。 */
(function () {
  "use strict";
  var root = document.getElementById("demo-ctx-choice");
  if (!root) return;

  var NAMES = { "continue": "继续", rewind: "回退", compact: "压缩", clear: "清空", sub: "派子代理" };

  // 每个情景：题面、最优动作、决定它的问题、五个动作各自的解释
  var SCENES = [
    {
      text: "上午修完了登录接口的 500。下午你在同一个会话里问：首页推荐位为什么不刷新？",
      best: "clear",
      why: {
        "continue": "上午那摞日志和“探活超时是根因”的结论会每轮重发，它会继续顺着上午的思路走，就是本章开头那一幕。",
        rewind: "回退只能退到某次提问之前。退到第一问之前，效果等于清空，只是多绕了一步。",
        compact: "摘要会把“探活超时是根因”当成进度留下来。误导还在，只是变短了。",
        clear: "第 ① 问就答“是”：换了一件事。清空后，上午如果有要带走的结论，写成交接便条带进来。",
        sub: "子代理只管它自己那段探索，主会话里那一上午的历史一点没少。"
      }
    },
    {
      text: "还是登录 500。它判断是超时太短，连着三轮把超时从 2 秒改到 60 秒，500 还在。你发现该查的是探活路径写错了。",
      best: "rewind",
      why: {
        "continue": "在后面追加一句“不对”，三轮错路和你的纠正会同时留在历史里，它可能又被拉回“改超时”。",
        rewind: "第 ① 问否，第 ② 问是。退回到三轮之前那次提问，改写提问，点明先查探活路径。别忘了那三轮改过的文件：连代码一起回退，或者用 git 还原。",
        compact: "摘要会把“超时已调到 60 秒”当成已做的决策写进去，错路从原文变成了“事实”。",
        clear: "能用，但前面有效的定位过程也一起没了。只有错路很长、有效部分很少时才划算。",
        sub: "错路已经在主会话里了，子代理拿不走它。"
      }
    },
    {
      text: "同一个问题，方向是对的。但前面二十轮读了大量日志，占用到了 85%，后面还要连着改四个文件。",
      best: "compact",
      why: {
        "continue": "再读几个文件就会撞上软线，到时自动压缩会替你决定留什么。不如现在自己压，并写明保留什么。",
        rewind: "没有走错的轮次可剪；回退会把有效工作一起剪掉。",
        compact: "前两问都是“否”，第 ③ 问是“是”。用 /compact 时补一句保留什么：根因结论、要改的四个文件路径、否掉的方案。",
        clear: "任务没换、还要接着往下做，清空后要重新交代的东西太多。你愿意自己写便条也行，但这里压缩更省事。",
        sub: "日志已经读进来了，子代理清不掉；它能帮的是后面那些还没发生的大块输出。"
      }
    },
    {
      text: "同一个问题，上下文还很干净。下一步要在 200 个测试文件里找出所有用到旧超时配置的地方，你只要一份清单。",
      best: "sub",
      why: {
        "continue": "让主会话自己搜，200 个文件的搜索输出会全部留在历史里，之后每轮都要重发。",
        rewind: "没有错路可剪。",
        compact: "现在没什么可压。等它搜完再压，等于先把垃圾搬进屋再扫。",
        clear: "任务没换，清空会丢掉需要的背景。",
        sub: "前三问都是“否”，第 ④ 问是“是”。任务说明要写全（子代理看不到主会话），并让它只带回“文件:行号”清单。"
      }
    },
    {
      text: "任务已经做完，你只想问一句：刚才那个配置项叫什么来着？",
      best: "continue",
      why: {
        "continue": "四问都是“否”：同一件事、没走错、一句话塞不满窗口、也不会产生大块输出。直接问，问完再清空。",
        rewind: "什么都不用剪。",
        compact: "为一句话付一次模型调用，还可能把这个配置名压没了。",
        clear: "清空后这个名字就没了。先问，再清空。",
        sub: "子代理看不到主会话，它不知道“刚才”指的是什么。"
      }
    }
  ];

  var select = root.querySelector("#demo-ctx-choice-select");
  var scene = root.querySelector("#demo-ctx-choice-scene");
  var feedback = root.querySelector("#demo-ctx-choice-feedback");
  var score = root.querySelector("#demo-ctx-choice-score");
  var buttons = root.querySelectorAll("[data-act]");
  var idle = feedback.textContent;

  // first[i]：第 i 个情景第一次选的动作；不重复计分
  var first = [];
  var picked = [];

  function scoreText() {
    var n = 0;
    for (var i = 0; i < SCENES.length; i++) if (first[i] && first[i] === SCENES[i].best) n++;
    var answered = 0;
    for (var j = 0; j < SCENES.length; j++) if (first[j]) answered++;
    return "第一次就选对：" + n + " / " + SCENES.length + (answered ? "（已答 " + answered + " 个）" : "");
  }

  function render() {
    var i = Number(select.value);
    var s = SCENES[i];
    scene.innerHTML = "";
    var b = document.createElement("b");
    b.textContent = "情景 " + (i + 1);
    scene.appendChild(b);
    scene.appendChild(document.createTextNode(s.text));

    var act = picked[i];
    for (var k = 0; k < buttons.length; k++) {
      buttons[k].setAttribute("aria-pressed", buttons[k].getAttribute("data-act") === act ? "true" : "false");
    }
    if (!act) {
      feedback.textContent = idle;
      feedback.removeAttribute("data-state");
    } else {
      var ok = act === s.best;
      feedback.setAttribute("data-state", ok ? "ok" : "bad");
      feedback.innerHTML = "";
      var head = document.createElement("strong");
      head.textContent = ok ? "选对了：" + NAMES[act] + "。" : NAMES[act] + "不是最优。";
      feedback.appendChild(head);
      feedback.appendChild(document.createTextNode(s.why[act]));
    }
    score.textContent = scoreText();
  }

  for (var k = 0; k < buttons.length; k++) {
    buttons[k].addEventListener("click", function (e) {
      var i = Number(select.value);
      var act = e.currentTarget.getAttribute("data-act");
      if (!first[i]) first[i] = act;
      picked[i] = act;
      render();
    });
  }
  select.addEventListener("change", render);
  root.querySelector("#demo-ctx-choice-next").addEventListener("click", function () {
    select.value = String((Number(select.value) + 1) % SCENES.length);
    render();
  });
  root.querySelector("#demo-ctx-choice-reset").addEventListener("click", function () {
    first = [];
    picked = [];
    select.value = "0";
    render();
  });

  render();
})();
