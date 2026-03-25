const API = '';

async function loadFilters() {
  const res = await fetch(`${API}/api/filters`);
  const data = await res.json();
  fillSelect('region', data.regions);
  fillSelect('category', data.categories);
  fillSelect('businessType', data.business_types);
}

function fillSelect(id, items) {
  const el = document.getElementById(id);
  items.forEach(item => {
    const opt = document.createElement('option');
    opt.value = item; opt.textContent = item;
    el.appendChild(opt);
  });
}

let ageInputMode = 'direct'; // 'direct' | 'birth'

function toggleAgeInput() {
  const link = document.getElementById('ageToggle');
  const directWrap = document.getElementById('ageDirectWrap');
  const birthWrap = document.getElementById('ageBirthWrap');

  if (ageInputMode === 'direct') {
    ageInputMode = 'birth';
    directWrap.style.display = 'none';
    birthWrap.style.display = 'block';
    link.textContent = '직접 입력';
    document.getElementById('age').value = '';
  } else {
    ageInputMode = 'direct';
    directWrap.style.display = 'block';
    birthWrap.style.display = 'none';
    link.textContent = '생년월일로 입력';
    document.getElementById('birthDate').value = '';
    document.getElementById('ageResult').textContent = '';
  }
}

function calcAge() {
  const birthVal = document.getElementById('birthDate').value;
  if (!birthVal) return;
  const birth = new Date(birthVal);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const mDiff = today.getMonth() - birth.getMonth();
  if (mDiff < 0 || (mDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  if (age < 0 || age > 150) {
    document.getElementById('ageResult').textContent = '올바른 생년월일을 입력하세요';
    document.getElementById('age').value = '';
    return;
  }
  document.getElementById('age').value = age;
  document.getElementById('ageResult').textContent = '만 ' + age + '세';
}

function toggleIncomeGuide() {
  document.getElementById('incomeGuide').classList.toggle('active');
}

async function search() {
  const params = new URLSearchParams();
  const age = document.getElementById('age').value;
  const gender = document.getElementById('gender').value;
  const region = document.getElementById('region').value;
  const category = document.getElementById('category').value;
  const biz = document.getElementById('businessType').value;
  const income = document.getElementById('income').value;
  const kw = document.getElementById('keyword').value;

  if (age) params.set('age', age);
  if (gender) params.set('gender', gender);
  if (region) params.set('region', region);
  if (category) params.set('category', category);
  if (biz) params.set('business_type', biz);
  if (income) params.set('income_percentile', income);
  if (kw) params.set('keyword', kw);

  const res = await fetch(`${API}/api/subsidies?${params}`);
  const data = await res.json();
  renderResults(data);
}

function genderBadge(g) {
  if (g === '여성') return '<span class="badge badge-gender">여성 전용</span>';
  if (g === '남성') return '<span class="badge badge-gender-m">남성 전용</span>';
  return '';
}

function renderResults(data) {
  document.getElementById('resultCount').innerHTML =
    `총 <strong>${data.count}건</strong>의 보조금을 찾았습니다`;

  if (data.count === 0) {
    document.getElementById('results').innerHTML =
      '<div class="empty-state"><div class="icon">&#128270;</div><p>조건에 맞는 보조금이 없습니다.<br>검색 조건을 변경해보세요.</p></div>';
    return;
  }

  document.getElementById('results').innerHTML = data.results.map(s => `
    <div class="card" onclick="showDetail('${s.id}')" style="cursor:pointer">
      <div class="card-header">
        <span class="card-title">${s.name}</span>
        <span>
          <span class="badge">${s.category}</span>
          ${genderBadge(s.gender)}
        </span>
      </div>
      <div class="card-desc">${s.description}</div>
      <div class="card-meta">
        <span>&#127974; ${s.organization}</span>
        <span>&#128176; ${s.amount}</span>
        <span>&#128197; ~${s.deadline || '상시'}</span>
        <span>&#128100; 만 ${s.age_min != null ? s.age_min : '?'}~${s.age_max != null ? s.age_max : '?'}세</span>
      </div>
      <div class="tag-list">
        ${s.region.slice(0, 5).map(r => `<span class="tag">${r}</span>`).join('')}
        ${s.region.length > 5 ? `<span class="tag">+${s.region.length - 5}</span>` : ''}
      </div>
    </div>
  `).join('');
}

async function showDetail(id) {
  const res = await fetch(`${API}/api/subsidies/${id}`);
  const s = await res.json();

  document.getElementById('modalContent').innerHTML = `
    <button class="modal-close" onclick="closeModal(event, true)">&times;</button>
    <h2>${s.name}</h2>
    <span class="badge">${s.category}</span> ${genderBadge(s.gender)}
    <p style="margin: 1rem 0; color: #475569;">${s.description}</p>
    <div class="detail-row"><span class="detail-label">지원금액</span> ${s.amount}</div>
    <div class="detail-row"><span class="detail-label">연령</span> 만 ${s.age_min != null ? s.age_min : '?'}세 ~ ${s.age_max != null ? s.age_max : '?'}세</div>
    <div class="detail-row"><span class="detail-label">성별</span> ${!s.gender ? '제한 없음' : s.gender + ' 전용'}</div>
    <div class="detail-row"><span class="detail-label">소득기준</span> ${!s.income_percentile || s.income_percentile >= 100 ? '제한 없음' : `소득분위 ${s.income_percentile}% 이하`}</div>
    <div class="detail-row"><span class="detail-label">지역</span> ${s.region.join(', ')}</div>
    <div class="detail-row"><span class="detail-label">업종</span> ${s.business_types.length ? s.business_types.join(', ') : '제한 없음'}</div>
    <div class="detail-row"><span class="detail-label">신청마감</span> ${s.deadline || '상시'}</div>
    <div class="detail-row"><span class="detail-label">주관기관</span> ${s.organization}</div>
    <div class="detail-row"><span class="detail-label">필요서류</span> ${s.documents.join(', ') || '정보 없음'}</div>
  `;
  document.getElementById('modal').classList.add('active');
}

function closeModal(e, force) {
  if (force || e.target === document.getElementById('modal')) {
    document.getElementById('modal').classList.remove('active');
  }
}

function resetFilters() {
  document.getElementById('age').value = '';
  document.getElementById('birthDate').value = '';
  document.getElementById('ageResult').textContent = '';
  if (ageInputMode === 'birth') toggleAgeInput();
  document.getElementById('gender').value = '';
  document.getElementById('region').value = '';
  document.getElementById('category').value = '';
  document.getElementById('businessType').value = '';
  document.getElementById('income').value = '';
  document.getElementById('keyword').value = '';
  search();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(e, true); });
loadFilters();
search();
