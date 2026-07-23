// 아임웹 상품 요약설명 도우미 — 팝업 UI
// 아이콘을 누른 순간에만 동작한다(activeTab). 활성 탭에서 상품명·카테고리를 읽어
// 초안을 만들고, chrome.scripting(MAIN world)으로 페이지의 Froala 에디터에 적용한다.
'use strict';

const TONES = ['정중한', '감성적', '간결한'];
const KINDS = ['핵심 소개', '감성 어필', '혜택 강조'];

// ---------- 한국어 조사 (받침 판별) ----------
const hasBatchim = (word) => {
  const ch = (word || '').trim().replace(/[^가-힣a-zA-Z0-9]+$/, '').slice(-1);
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 > 0;
  return null; // 한글이 아니면 판단 불가 → 병기
};
const josa = (word, withB, withoutB) => {
  const b = hasBatchim(word);
  if (b === null) return withB + '(' + withoutB + ')';
  return b ? withB : withoutB;
};

// ---------- 초안 템플릿 (톤 3종 x 문형 3종) ----------
const TEMPLATES = {
  '정중한': {
    '핵심 소개': (n, c) => `${n}${josa(n, '은', '는')} 엄선한 성분과 검증된 품질로 완성한 ${c}입니다. 매일의 루틴에 신뢰할 수 있는 선택이 되어드립니다.`,
    '감성 어필': (n, c) => `정성껏 완성한 ${c}, ${n}${josa(n, '과', '와')} 함께 일상의 순간이 한층 특별해집니다.`,
    '혜택 강조': (n, c) => `${n}${josa(n, '을', '를')} 지금 만나보세요. 합리적인 가격과 매장 픽업으로 더 빠르고 편리하게 받아보실 수 있습니다.`
  },
  '감성적': {
    '핵심 소개': (n, c) => `하루의 끝, ${n}${josa(n, '이', '가')} 건네는 작은 위로. 자연에서 찾은 성분이 피부 위에 부드럽게 스며듭니다.`,
    '감성 어필': (n, c) => `빛나는 순간은 매일 만들어집니다. ${n}${josa(n, '과', '와')} 함께 나만의 리추얼을 시작해보세요.`,
    '혜택 강조': (n, c) => `오늘의 나에게 건네는 선물, ${n}. 지금 가장 좋은 계절을 특별한 혜택과 함께 담아보세요.`
  },
  '간결한': {
    '핵심 소개': (n, c) => `${n} — 매일 쓰는 ${c}의 기준. 꼭 필요한 것만 담았습니다.`,
    '감성 어필': (n, c) => `피부가 먼저 아는 차이, ${n}.`,
    '혜택 강조': (n, c) => `${n}, 지금 주문하면 매장 픽업으로 바로 수령할 수 있습니다.`
  }
};

// ---------- 페이지에서 실행되는 함수 (자체 완결 — 외부 참조 금지) ----------
const PAGE_READ = () => {
  const clean = (s) => (s || '').replace(/[​×]/g, '').trim();
  const findLabel = (prefix) => {
    const labels = document.querySelectorAll('label');
    for (let i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || '').trim().startsWith(prefix)) return labels[i];
    }
    return null;
  };
  const lab = findLabel('요약 설명');
  let el = null, node = lab && lab.parentElement, hops = 0;
  while (node && hops < 5) {
    el = node.querySelector('.fr-element');
    if (el) break;
    node = node.parentElement; hops++;
  }
  if (!el) return { ok: false };
  let name = '';
  let n2 = findLabel('상품명'), h2 = 0;
  while (n2 && h2 < 5) {
    const inp = n2.querySelector && n2.querySelector('input');
    if (inp && inp.value) { name = clean(inp.value); break; }
    n2 = n2.parentElement; h2++;
  }
  let cat = '';
  let n3 = findLabel('카테고리'), h3 = 0;
  while (n3 && h3 < 5) {
    if (n3.querySelectorAll) {
      const spans = n3.querySelectorAll('span,div');
      const texts = [];
      for (let i = 0; i < spans.length; i++) {
        const t = clean(spans[i].textContent);
        if (t && t.length < 25 && !t.includes('카테고리')) texts.push(t);
      }
      if (texts.length) { cat = texts[0]; break; }
    }
    n3 = n3.parentElement; h3++;
  }
  return { ok: true, name, cat };
};

const PAGE_APPLY = (text) => {
  const findLabel = (prefix) => {
    const labels = document.querySelectorAll('label');
    for (let i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || '').trim().startsWith(prefix)) return labels[i];
    }
    return null;
  };
  const lab = findLabel('요약 설명');
  let el = null, node = lab && lab.parentElement, hops = 0;
  while (node && hops < 5) {
    el = node.querySelector('.fr-element');
    if (el) break;
    node = node.parentElement; hops++;
  }
  if (!el) return { ok: false };
  const esc = text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const html = '<p>' + esc + '</p>';
  const F = window.FroalaEditor;
  let inst = null;
  if (F && F.INSTANCES) {
    for (let i = 0; i < F.INSTANCES.length; i++) {
      const cand = F.INSTANCES[i];
      if (cand.el === el || (cand.$el && cand.$el[0] === el)) { inst = cand; break; }
    }
  }
  if (inst) {
    inst.html.set(html);
    if (inst.undo && inst.undo.saveStep) inst.undo.saveStep();
    inst.events.trigger('contentChanged');
  } else {
    el.innerHTML = html;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }
  return { ok: true };
};

// ---------- 팝업 로직 ----------
const $ = (id) => document.getElementById(id);
let tabId = null;
let ctx = null;
let toneIdx = 0;
let kindIdx = 0;

const exec = async (func, args) => {
  const out = await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func,
    args: args || []
  });
  return out && out[0] && out[0].result;
};

const renderTones = () => {
  const btns = $('tones').querySelectorAll('button');
  for (let i = 0; i < btns.length; i++) btns[i].classList.toggle('on', i === toneIdx);
};

const regenerate = () => {
  const name = (ctx && ctx.name) || '이 상품';
  const cat = (ctx && ctx.cat) || '제품';
  $('preview').value = TEMPLATES[TONES[toneIdx]][KINDS[kindIdx]](name, cat);
  updateLen();
};

const updateLen = () => { $('plen').textContent = $('preview').value.length + '자'; };

const init = async () => {
  for (let i = 0; i < TONES.length; i++) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = TONES[i];
    b.addEventListener('click', () => {
      toneIdx = i; kindIdx = 0;
      try { localStorage.setItem('tone', String(i)); } catch (e) { /* 무시 */ }
      renderTones(); regenerate();
    });
    $('tones').appendChild(b);
  }
  $('reroll').addEventListener('click', () => { kindIdx = (kindIdx + 1) % KINDS.length; regenerate(); });
  $('preview').addEventListener('input', updateLen);
  $('apply').addEventListener('click', async () => {
    const text = $('preview').value.trim();
    if (!text) return;
    const btn = $('apply');
    btn.disabled = true;
    let res = null;
    try { res = await exec(PAGE_APPLY, [text]); } catch (e) { res = null; }
    if (res && res.ok) {
      btn.textContent = '적용 완료';
      btn.classList.add('done');
      setTimeout(() => window.close(), 600);
    } else {
      btn.textContent = '적용 실패 — 화면을 새로고침해 주세요';
      btn.disabled = false;
    }
  });

  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  tabId = tabs && tabs[0] && tabs[0].id;
  let res = null;
  try { res = await exec(PAGE_READ); } catch (e) { res = null; }
  if (!res || !res.ok) {
    $('empty').hidden = false;
    return;
  }
  ctx = res;
  $('ctx').textContent = [ctx.name, ctx.cat].filter(Boolean).join(' · ');
  try { toneIdx = Math.min(TONES.length - 1, Math.max(0, parseInt(localStorage.getItem('tone') || '0', 10) || 0)); } catch (e) { /* 무시 */ }
  $('main').hidden = false;
  renderTones();
  regenerate();
};

init();
