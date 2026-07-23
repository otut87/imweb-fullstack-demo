// 아임웹 상품 요약설명 도우미 — content script (MAIN world)
// 관리자 상품 편집 화면의 "요약 설명" Froala 에디터에 토글형 초안 생성 패널을 붙인다.
// 기본은 접힘 — 에디터 툴바 우측의 칩을 눌러 연다. 페이지 컨텍스트에서 실행되므로
// window.FroalaEditor 인스턴스에 직접 접근할 수 있다.
(() => {
  'use strict';
  if (window.__iwSummaryHelperLoaded) return;
  window.__iwSummaryHelperLoaded = true;

  const PANEL_ID = 'iw-sum-helper';
  const CHIP_ID = 'iwsh-chip';
  const OPEN_KEY = 'iwshOpen';  // 열림 상태 기억 (localStorage)
  const REC_MIN = 80;   // 메타 설명 권장 최소 글자수
  const REC_MAX = 160;  // 메타 설명 권장 최대 글자수
  const UNDO_MAX = 10;

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
  const TONES = ['정중한', '감성적', '간결한'];
  const KINDS = ['핵심 소개', '감성 어필', '혜택 강조'];
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

  // ---------- 페이지 DOM 접근 ----------
  const findLabel = (prefix) => {
    const labels = document.querySelectorAll('label');
    for (let i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || '').trim().startsWith(prefix)) return labels[i];
    }
    return null;
  };

  const clean = (s) => (s || '').replace(/[​×]/g, '').trim();

  const getProductName = () => {
    const lab = findLabel('상품명');
    let node = lab, hops = 0;
    while (node && hops < 5) {
      const inp = node.querySelector && node.querySelector('input');
      if (inp && inp.value) return clean(inp.value);
      node = node.parentElement; hops++;
    }
    return '';
  };

  const getFirstCategory = () => {
    const lab = findLabel('카테고리');
    let node = lab, hops = 0;
    while (node && hops < 5) {
      if (node.querySelectorAll) {
        const texts = [];
        const spans = node.querySelectorAll('span,div');
        for (let i = 0; i < spans.length; i++) {
          const t = clean(spans[i].textContent);
          if (t && t.length < 25 && !t.includes('카테고리')) texts.push(t);
        }
        if (texts.length) return texts[0];
      }
      node = node.parentElement; hops++;
    }
    return '';
  };

  // 요약 설명 라벨을 기준으로 해당 섹션의 에디터만 찾는다 (상세 설명 에디터와 혼동 방지)
  const getEditorParts = () => {
    const lab = findLabel('요약 설명');
    if (!lab) return null;
    let node = lab.parentElement, hops = 0;
    while (node && hops < 5) {
      const el = node.querySelector('.fr-element');
      if (el) return { label: lab, wrap: node, box: el.closest('.fr-box'), el };
      node = node.parentElement; hops++;
    }
    return null;
  };

  const getInstance = (el) => {
    const F = window.FroalaEditor;
    if (!F || !F.INSTANCES) return null;
    for (let i = 0; i < F.INSTANCES.length; i++) {
      const inst = F.INSTANCES[i];
      if (inst.el === el || (inst.$el && inst.$el[0] === el)) return inst;
    }
    return null;
  };

  const escapeHtml = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const getEditorHtml = (el) => { const inst = getInstance(el); return inst ? inst.html.get() : el.innerHTML; };
  const getEditorText = (el) => clean(el.innerText);
  const setEditorHtml = (el, html) => {
    const inst = getInstance(el);
    if (inst) {
      inst.html.set(html);
      if (inst.undo && inst.undo.saveStep) inst.undo.saveStep();
      inst.events.trigger('contentChanged');
    } else {
      el.innerHTML = html;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
  };
  const setEditorText = (el, text) => setEditorHtml(el, '<p>' + escapeHtml(text) + '</p>');

  // ---------- 패널 ----------
  const STYLE = `
#${CHIP_ID}{position:absolute;top:5px;right:8px;z-index:20;border:1px solid #d1d5db;background:#fff;color:#374151;border-radius:999px;padding:3px 10px;font-size:11.5px;line-height:1.4;cursor:pointer;font-family:inherit}
#${CHIP_ID}:hover{border-color:#9ca3af}
#${CHIP_ID}.on{background:#111827;border-color:#111827;color:#fff}
#${PANEL_ID}{border:1px solid #e5e7eb;background:#fafafa;border-radius:10px;padding:10px 12px;margin:8px 0 10px;font-size:12.5px;color:#374151;display:flex;flex-direction:column;gap:8px;font-family:inherit}
#${PANEL_ID} .iwsh-head{display:flex;align-items:center;justify-content:space-between}
#${PANEL_ID} .iwsh-title{font-weight:700;color:#111827}
#${PANEL_ID} .iwsh-headright{display:flex;align-items:center;gap:10px}
#${PANEL_ID} .iwsh-count{font-variant-numeric:tabular-nums;color:#6b7280}
#${PANEL_ID} .iwsh-count.ok{color:#059669}
#${PANEL_ID} .iwsh-count.over{color:#dc2626}
#${PANEL_ID} .iwsh-close{border:0;background:transparent;color:#6b7280;font-size:16px;line-height:1;cursor:pointer;padding:2px 4px;font-family:inherit}
#${PANEL_ID} .iwsh-close:hover{color:#111827}
#${PANEL_ID} .iwsh-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#${PANEL_ID} .iwsh-seg{display:inline-flex;border:1px solid #d1d5db;border-radius:8px;overflow:hidden;background:#fff}
#${PANEL_ID} .iwsh-seg button{border:0;background:#fff;padding:5px 12px;font-size:12.5px;cursor:pointer;color:#374151;font-family:inherit}
#${PANEL_ID} .iwsh-seg button+button{border-left:1px solid #e5e7eb}
#${PANEL_ID} .iwsh-seg button.on{background:#111827;color:#fff}
#${PANEL_ID} select{border:1px solid #d1d5db;border-radius:8px;padding:5px 8px;background:#fff;font-size:12.5px;color:#374151;font-family:inherit}
#${PANEL_ID} .iwsh-btn{border:1px solid #d1d5db;background:#fff;border-radius:8px;padding:5px 12px;font-size:12.5px;cursor:pointer;color:#374151;font-family:inherit}
#${PANEL_ID} .iwsh-btn:disabled{opacity:.45;cursor:default}
#${PANEL_ID} .iwsh-primary{background:#111827;border-color:#111827;color:#fff}
#${PANEL_ID} textarea{width:100%;box-sizing:border-box;border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;line-height:1.5;resize:vertical;background:#fff;color:#111827;font-family:inherit}
#${PANEL_ID} .iwsh-foot{display:flex;justify-content:space-between;gap:8px;color:#9ca3af;font-size:11.5px}
`;

  const buildPanel = () => {
    const panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <div class="iwsh-head">
        <span class="iwsh-title">요약설명 도우미</span>
        <span class="iwsh-headright">
          <span class="iwsh-count" data-role="count">-</span>
          <button type="button" class="iwsh-close" data-role="close" aria-label="닫기">&#215;</button>
        </span>
      </div>
      <div class="iwsh-row">
        <div class="iwsh-seg" data-role="tones"></div>
        <select data-role="kind"></select>
        <button type="button" class="iwsh-btn iwsh-primary" data-role="apply">에디터에 적용</button>
        <button type="button" class="iwsh-btn" data-role="undo" disabled>되돌리기</button>
      </div>
      <textarea rows="2" spellcheck="false" data-role="preview"></textarea>
      <div class="iwsh-foot">
        <span data-role="plen"></span>
        <span>상품명·카테고리를 자동 반영한 초안입니다. 자유롭게 수정 후 적용하세요.</span>
      </div>`;
    return panel;
  };

  const mount = (parts) => {
    if (!document.getElementById('iwsh-style')) {
      const st = document.createElement('style');
      st.id = 'iwsh-style';
      st.textContent = STYLE;
      document.head.appendChild(st);
    }
    // 재마운트 시 남아있을 수 있는 이전 칩 정리
    const leftoverChip = document.getElementById(CHIP_ID);
    if (leftoverChip) leftoverChip.remove();

    // 토글 칩 — 에디터 툴바 우측 빈 공간에 얹는다 (레이아웃 밀지 않음)
    const box = parts.box;
    if (getComputedStyle(box).position === 'static') box.style.position = 'relative';
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.id = CHIP_ID;
    chip.textContent = '요약설명 도우미';
    box.appendChild(chip);

    // 패널은 항상 DOM에 두되(감지 가드용) 접힘 상태는 display로 제어
    // .fr-box는 라벨의 부모(wrap)보다 안쪽에 중첩되어 있으므로 반드시 box의 실제 부모 기준으로 삽입한다
    const panel = buildPanel();
    box.parentElement.insertBefore(panel, box);

    const q = (role) => panel.querySelector(`[data-role="${role}"]`);
    const tonesBox = q('tones'), kindSel = q('kind'), preview = q('preview');
    const applyBtn = q('apply'), undoBtn = q('undo'), countEl = q('count'), plenEl = q('plen');
    const undoStack = [];
    let tone = TONES[0];

    for (let i = 0; i < TONES.length; i++) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = TONES[i];
      if (i === 0) b.classList.add('on');
      b.addEventListener('click', () => {
        tone = TONES[i];
        const btns = tonesBox.querySelectorAll('button');
        for (let k = 0; k < btns.length; k++) btns[k].classList.toggle('on', btns[k] === b);
        regenerate();
      });
      tonesBox.appendChild(b);
    }
    for (let i = 0; i < KINDS.length; i++) {
      const o = document.createElement('option');
      o.value = KINDS[i]; o.textContent = KINDS[i];
      kindSel.appendChild(o);
    }
    kindSel.addEventListener('change', regenerate);

    function regenerate() {
      const name = getProductName() || '이 상품';
      const cat = getFirstCategory() || '제품';
      preview.value = TEMPLATES[tone][kindSel.value || KINDS[0]](name, cat);
      updatePreviewLen();
    }
    function updatePreviewLen() { plenEl.textContent = '초안 ' + preview.value.length + '자'; }
    preview.addEventListener('input', updatePreviewLen);

    function updateCount() {
      const len = getEditorText(parts.el).length;
      countEl.textContent = '에디터 ' + len + '자 · 권장 ' + REC_MIN + '~' + REC_MAX;
      countEl.classList.toggle('ok', len >= REC_MIN && len <= REC_MAX);
      countEl.classList.toggle('over', len > REC_MAX);
    }

    applyBtn.addEventListener('click', () => {
      undoStack.push(getEditorHtml(parts.el));
      if (undoStack.length > UNDO_MAX) undoStack.shift();
      setEditorText(parts.el, preview.value.trim());
      undoBtn.disabled = false;
      updateCount();
    });
    undoBtn.addEventListener('click', () => {
      const prev = undoStack.pop();
      if (prev !== undefined) setEditorHtml(parts.el, prev);
      undoBtn.disabled = undoStack.length === 0;
      updateCount();
    });

    const inst = getInstance(parts.el);
    if (inst) {
      inst.events.on('contentChanged', updateCount);
      inst.events.on('keyup', updateCount);
    } else {
      parts.el.addEventListener('input', updateCount);
    }

    // 열기/닫기 — 칩 토글 + 패널 닫기 버튼, 상태는 localStorage에 기억
    const setOpen = (open) => {
      panel.style.display = open ? '' : 'none';
      chip.classList.toggle('on', open);
      try { localStorage.setItem(OPEN_KEY, open ? '1' : '0'); } catch (e) { /* 프라이빗 모드 등 — 무시 */ }
      if (open) updateCount();
    };
    chip.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      setOpen(panel.style.display === 'none');
    });
    q('close').addEventListener('click', () => setOpen(false));

    regenerate();
    updateCount();
    let openInit = false;
    try { openInit = localStorage.getItem(OPEN_KEY) === '1'; } catch (e) { /* 무시 */ }
    setOpen(openInit);
  };

  // SPA 전환·늦은 렌더에 대응: 즉시 1회 + 폴링으로 에디터 등장을 감지해 (재)마운트
  const tryMount = () => {
    if (document.getElementById(PANEL_ID)) return;
    const parts = getEditorParts();
    if (parts && parts.box) mount(parts);
  };
  tryMount();
  setInterval(tryMount, 800);
})();
