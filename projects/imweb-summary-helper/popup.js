// 아임웹 상품 요약설명 도우미 — 팝업 UI (v2.3)
// 아이콘을 누른 순간에만 동작한다(activeTab). 활성 탭에서 상품 정보(상품명·카테고리·가격·기존 요약)를
// 읽고, 데모 서버 프록시(/api/summary — 서버가 Claude Haiku 호출)로 맞춤 요약설명 3안을 생성해
// Froala 에디터에 적용한다. 키·설정 없이 바로 작동하며, 생성 실패 시 내장 템플릿으로 폴백한다.
'use strict';

// 데모 서버 프록시 — API 키는 서버 .env에만 존재(확장·저장소 미포함), IP당 레이트리밋
const PROXY_URL = 'https://15.165.133.165.sslip.io/api/summary';

const TONES = ['정중한', '감성적', '간결한'];
const TONE_DESC = ['정중한 — 격식 있고 신뢰감 있게', '감성적 — 감각적이고 서정적으로', '간결한 — 짧고 임팩트 있게'];
const KINDS = ['핵심 소개', '감성 어필', '혜택 강조']; // 템플릿 폴백용

// ---------- 한국어 조사 (받침 판별) ----------
const hasBatchim = (word) => {
  const ch = (word || '').trim().replace(/[^가-힣a-zA-Z0-9]+$/, '').slice(-1);
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 > 0;
  return null;
};
const josa = (word, withB, withoutB) => {
  const b = hasBatchim(word);
  if (b === null) return withB + '(' + withoutB + ')';
  return b ? withB : withoutB;
};

// ---------- 템플릿 (서버 생성 실패 시 폴백) ----------
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
  const inputNear = (prefix) => {
    let node = findLabel(prefix), hops = 0;
    while (node && hops < 5) {
      const inp = node.querySelector && node.querySelector('input');
      if (inp && inp.value) return clean(inp.value);
      node = node.parentElement; hops++;
    }
    return '';
  };
  const lab = findLabel('요약 설명');
  let el = null, node = lab && lab.parentElement, hops = 0;
  while (node && hops < 5) {
    el = node.querySelector('.fr-element');
    if (el) break;
    node = node.parentElement; hops++;
  }
  if (!el) return { ok: false };
  const name = inputNear('상품명');
  const price = inputNear('판매가');
  let cats = [];
  let n3 = findLabel('카테고리'), h3 = 0;
  while (n3 && h3 < 5) {
    if (n3.querySelectorAll) {
      const spans = n3.querySelectorAll('span,div');
      const texts = [];
      for (let i = 0; i < spans.length; i++) {
        const t = clean(spans[i].textContent);
        if (t && t.length < 25 && !t.includes('카테고리') && texts.indexOf(t) < 0) texts.push(t);
      }
      if (texts.length) { cats = texts.slice(0, 5); break; }
    }
    n3 = n3.parentElement; h3++;
  }
  return { ok: true, name, cats, price, summary: clean(el.innerText).slice(0, 300) };
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
let kindIdx = 0;       // 템플릿 폴백 로테이션
let candidates = [];   // AI 생성 결과 (최대 3안)
let candIdx = 0;

const exec = async (func, args) => {
  const out = await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func,
    args: args || []
  });
  return out && out[0] && out[0].result;
};

const setHint = (msg, isErr) => {
  const h = $('hint');
  h.textContent = msg || '';
  h.classList.toggle('err', !!isErr);
};

const updateLen = () => { $('plen').textContent = $('preview').value.length + '자'; };

const renderTones = () => {
  const btns = $('tones').querySelectorAll('button');
  for (let i = 0; i < btns.length; i++) btns[i].classList.toggle('on', i === toneIdx);
};

const showCandidate = () => {
  $('preview').value = candidates[candIdx] || '';
  updateLen();
  const r = $('reroll');
  r.hidden = candidates.length < 2;
  r.textContent = '다른 안 (' + (candIdx + 1) + '/' + candidates.length + ')';
};

const templateFill = () => {
  candidates = [];
  const name = (ctx && ctx.name) || '이 상품';
  const cat = (ctx && ctx.cats && ctx.cats[0]) || '제품';
  $('preview').value = TEMPLATES[TONES[toneIdx]][KINDS[kindIdx]](name, cat);
  updateLen();
  const r = $('reroll');
  r.hidden = false;
  r.textContent = '다른 문구';
};

const generate = async () => {
  const btn = $('gen');
  if (btn.disabled) return;  // 생성 중 재진입 방지(Enter 연타·중복 요청 차단)
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = '생성 중...';
  try {
    const res = await fetch(PROXY_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: (ctx && ctx.name) || '',
        cats: (ctx && ctx.cats) || [],
        price: (ctx && ctx.price) || '',
        summary: (ctx && ctx.summary) || '',
        keywords: $('kw').value.trim(),
        tone: TONE_DESC[toneIdx]
      })
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error((data && data.detail) || ('HTTP ' + res.status));
    const arr = data && data.drafts;
    if (!Array.isArray(arr)) throw new Error('응답 형식 오류');
    candidates = arr.filter((x) => typeof x === 'string' && x.trim()).slice(0, 5);
    if (!candidates.length) throw new Error('응답 형식 오류');
    candIdx = 0;
    showCandidate();
    setHint('');
  } catch (e) {
    kindIdx = 0;
    templateFill();
    setHint('AI 생성 실패(' + (e && e.message ? e.message : e) + ') — 템플릿 문구로 대체했습니다.', true);
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
};

const init = async () => {
  for (let i = 0; i < TONES.length; i++) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = TONES[i];
    b.addEventListener('click', () => {
      toneIdx = i;
      try { localStorage.setItem('tone', String(i)); } catch (e) { /* 무시 */ }
      renderTones();
      if (candidates.length) setHint('톤이 바뀌었습니다 — [AI 초안 생성]을 다시 눌러주세요.');
      else if ($('preview').value) { kindIdx = 0; templateFill(); }
    });
    $('tones').appendChild(b);
  }
  $('gen').addEventListener('click', generate);
  $('reroll').addEventListener('click', () => {
    if (candidates.length) { candIdx = (candIdx + 1) % candidates.length; showCandidate(); }
    else { kindIdx = (kindIdx + 1) % KINDS.length; templateFill(); }
  });
  $('preview').addEventListener('input', updateLen);
  $('kw').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.isComposing) generate();  // IME 조합 확정 Enter 무시
  });
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
  $('ctx').textContent = [ctx.name, ctx.cats && ctx.cats[0]].filter(Boolean).join(' · ');
  try { toneIdx = Math.min(TONES.length - 1, Math.max(0, parseInt(localStorage.getItem('tone') || '0', 10) || 0)); } catch (e) { /* 무시 */ }
  $('main').hidden = false;
  renderTones();
  setHint('[AI 초안 생성]을 누르면 상품 정보와 키워드로 맞춤 문구를 만듭니다.');
};

init();
