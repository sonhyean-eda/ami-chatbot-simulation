import os
import streamlit as st
from openai import OpenAI

# ------------------------------------------------------------
# 1. 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="AMI 챗봇 가상환자 시뮬레이션",
    page_icon="🫀",
    layout="wide"
)

# ------------------------------------------------------------
# 2. OpenAI 클라이언트 준비
# ------------------------------------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# ------------------------------------------------------------
# 3. 앱 제목
# ------------------------------------------------------------
st.title("🫀 급성심근경색(AMI) 챗봇 가상환자 시뮬레이션")
st.markdown("""
이 앱은 **규칙기반 시나리오 + OpenAI API(선택)** 방식의 예시입니다.

- 환자 상태, 활력징후, 검사결과, 처방은 **고정**
- OpenAI API는 **환자 말투를 자연스럽게 표현**하는 데만 사용 가능
- API 키가 없으면 **규칙기반 응답**으로 동작
""")

if not api_key:
    st.warning("OPENAI_API_KEY가 설정되지 않았습니다. 우선 규칙기반 응답만 사용됩니다.")

# ------------------------------------------------------------
# 4. 고정 데이터
# ------------------------------------------------------------
PATIENT_INFO = {
    "name": "김심근",
    "age": 62,
    "sex": "남성",
    "job": "택시 운전사",
    "chief_complaint": "가슴이 너무 조이고 답답하며 숨쉬기 힘들다.",
    "pain_location": "가슴 중앙",
    "pain_quality": "누가 꽉 쥐어짜는 듯한 통증",
    "radiation": "턱과 왼쪽 어깨",
    "onset": "30분 전 운전 중 갑자기 시작",
    "pain_score_initial": "8점",
    "associated_symptoms": "숨참, 식은땀, 극심한 불안",
    "history": "고혈압",
    "medication": "혈압약 복용 중 (약 이름은 모름)",
    "smoking": "오래 피웠고 하루 1갑 정도",
    "family_history": "아버지가 심장마비로 돌아가심",
    "allergy": "없었던 것 같음"
}

VITAL_SIGNS = {
    "BP": "168/96 mmHg",
    "HR": "104회/분",
    "RR": "24회/분",
    "SpO2": "93%",
    "BT": "36.7℃"
}

LAB_RESULTS = {
    "ECG": "ST-segment elevation 확인됨 (II, III, aVF)",
    "Troponin I": "0.5 ng/mL 상승",
    "CK-MB": "15 ng/mL 상승"
}

DOCTOR_ORDER = [
    "O2 2L/min via Nasal Cannula",
    "NTG 0.6mg SL",
    "Aspirin 300mg PO",
    "12-lead EKG Re-check"
]

DEBRIEFING_QUESTIONS = [
    "급성심근경색을 의심하게 한 핵심 단서는 무엇이었습니까?",
    "이번 시뮬레이션에서 가장 먼저 해야 한다고 판단한 우선순위 간호활동은 무엇이었습니까?",
    "환자의 불안을 완화하기 위해 사용한 치료적 의사소통은 무엇이었습니까?",
    "다음에 같은 상황을 경험한다면 보완하고 싶은 사정 또는 보고 내용은 무엇입니까?"
]

# ------------------------------------------------------------
# 5. 세션 상태 초기화
# ------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "started" not in st.session_state:
    st.session_state.started = False

if "ended" not in st.session_state:
    st.session_state.ended = False

if "vitals_shown" not in st.session_state:
    st.session_state.vitals_shown = False

if "labs_shown" not in st.session_state:
    st.session_state.labs_shown = False

if "order_shown" not in st.session_state:
    st.session_state.order_shown = False

if "intervention_done" not in st.session_state:
    st.session_state.intervention_done = False

if "reassessment_done" not in st.session_state:
    st.session_state.reassessment_done = False

if "show_debriefing" not in st.session_state:
    st.session_state.show_debriefing = False

if "debrief_submitted" not in st.session_state:
    st.session_state.debrief_submitted = False

if "checklist" not in st.session_state:
    st.session_state.checklist = {
        "초기 접촉 및 주호소 확인": False,
        "활력징후 확인 시도": False,
        "병력 및 위험요인 사정": False,
        "검사 시행 또는 결과 확인": False,
        "SBAR 보고 수행": False,
        "처방 기반 중재 수행": False,
        "중재 후 재사정 수행": False,
        "치료적 의사소통 사용": False,
        "디브리핑 참여": False
    }

# ------------------------------------------------------------
# 6. 사이드바
# ------------------------------------------------------------
st.sidebar.header("📋 진행 상태")
for key, value in st.session_state.checklist.items():
    st.sidebar.write(f"{'✅' if value else '⬜'} {key}")

st.sidebar.markdown("---")
st.sidebar.subheader("환자 기본 정보")
st.sidebar.write(f"이름: {PATIENT_INFO['name']}")
st.sidebar.write(f"성별/나이: {PATIENT_INFO['sex']} / {PATIENT_INFO['age']}세")
st.sidebar.write(f"직업: {PATIENT_INFO['job']}")

# ------------------------------------------------------------
# 7. 시작 / 초기화 버튼
# ------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("▶ 시뮬레이션 시작"):
        st.session_state.started = True
        st.session_state.ended = False
        st.session_state.vitals_shown = False
        st.session_state.labs_shown = False
        st.session_state.order_shown = False
        st.session_state.intervention_done = False
        st.session_state.reassessment_done = False
        st.session_state.show_debriefing = False
        st.session_state.debrief_submitted = False
        st.session_state.messages = []
        st.session_state.checklist = {
            "초기 접촉 및 주호소 확인": True,
            "활력징후 확인 시도": False,
            "병력 및 위험요인 사정": False,
            "검사 시행 또는 결과 확인": False,
            "SBAR 보고 수행": False,
            "처방 기반 중재 수행": False,
            "중재 후 재사정 수행": False,
            "치료적 의사소통 사용": False,
            "디브리핑 참여": False
        }
        st.session_state.messages.append({
            "role": "assistant",
            "content": "허억.. 선생님.. 가슴이 너무 조여요.. 너무 답답하고 숨쉬기가 힘들어요.. 저 죽는 거 아니죠?"
        })
        st.rerun()

with col2:
    if st.button("🔄 처음부터 다시 시작"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ------------------------------------------------------------
# 8. OpenAI로 말투 자연화
# ------------------------------------------------------------
def naturalize_with_openai(user_input: str, clinical_fact: str, tone: str = "불안하고 통증이 심한 상태") -> str:
    if client is None:
        return clinical_fact

    instructions = f"""
당신은 응급실에 내원한 62세 남성 급성심근경색 의심 환자 역할입니다.
현재 상태: {tone}

매우 중요한 규칙:
1. 아래 '핵심 정보'의 의미를 절대 바꾸지 마세요.
2. 숫자, 검사결과, 병력, 의학적 사실을 추가하거나 수정하지 마세요.
3. 학생이 묻지 않은 새로운 정보는 먼저 말하지 마세요.
4. 환자 입장에서 자연스럽고 감정이 느껴지게 한국어로 답하세요.
5. 환자는 불안, 통증, 두려움, 안도 같은 감정을 환자답게 표현할 수 있습니다.
6. 지나치게 딱딱하거나 보고식으로 말하지 말고, 실제 환자처럼 말하세요.
7. 너무 짧게 끊지 말고, 필요하면 2~4문장으로 답하세요.
8. 하지만 너무 길게 설명하지는 말고, 핵심만 자연스럽게 말하세요.
9. 의사나 간호사처럼 전문적으로 설명하지 말고, 환자처럼 체감 증상과 감정을 중심으로 말하세요.
10. 말끝은 자연스럽게 흐리거나 불안한 환자처럼 표현해도 됩니다. 예: "...", "무서워요", "괜찮은 거 맞나요?"
11. 핵심 정보가 짧더라도, 의미를 바꾸지 않는 범위에서 자연스러운 환자 말투로 풀어서 답하세요.
"""

    prompt = f"""
학생 입력:
{user_input}

핵심 정보:
{clinical_fact}

위 핵심 정보를 유지한 채, 실제 응급실 환자처럼 불안과 증상을 자연스럽게 드러내며 답하세요.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=instructions,
            input=prompt
        )
        text = response.output_text.strip()
        return text if text else clinical_fact
    except Exception:
        return clinical_fact

# ------------------------------------------------------------
# 9. 질문 분류
# ------------------------------------------------------------
def classify_input(user_text: str) -> str:
    text = user_text.lower().strip()

    # ------------------------------------------------------------
    # 0. 노티/SBAR 상세 보고 우선 판정
    # - "보고/노티/SBAR" 같은 행동 표현이 있어야만 report_detail
    # - 심전도, 혈액검사 같은 단어만 있다고 report_detail로 가지 않음
    # ------------------------------------------------------------
    report_action_keywords = [
        "보고", "보고드립니다", "보고 드립니다",
        "노티", "노티드립니다", "노티 드립니다",
        "sbar",
        "처방 부탁", "처방 부탁드립니다", "처방 요청",
        "의사에게 보고", "의사에게 노티",
        "의사선생님께 보고", "의사선생님께 노티"
    ]

    report_content_keywords = [
        "김심근 환자",
        "응급실 1번 침상",
        "30분 전 시작", "30분 전부터", "30분 전",
        "압박성 흉통", "흉통", "가슴 통증",
        "nrs 8점", "통증 8점",
        "고혈압 약 복용", "고혈압",
        "흡연력", "담배",
        "가족력",
        "심전도", "ekg", "ecg",
        "혈액검사", "피검사", "lab",
        "트로포닌", "troponin",
        "ck-mb", "ckmb",
        "급성심근경색", "stemi", "st 분절 상승", "st-segment elevation"
    ]

    has_report_action = any(k in text for k in report_action_keywords)
    has_report_content = any(k in text for k in report_content_keywords)

    if has_report_action and has_report_content:
        return "report_detail"

    # ------------------------------------------------------------
    # 1. 가족력
    # ------------------------------------------------------------
    family_history_keywords = [
        "가족력이", "가족력이 있으신가요", "가족력",
        "가족 중", "심장질환 가족력", "아버지", "어머니"
    ]
    if any(k in text for k in family_history_keywords):
        return "family_history"

    # ------------------------------------------------------------
    # 2. 단순 보고 예고
    # ------------------------------------------------------------
    simple_report_keywords = [
        "보고하도록 하겠습니다",
        "노티하도록 하겠습니다",
        "의사에게 보고하겠습니다",
        "의사에게 노티하겠습니다",
        "의사선생님께 보고하겠습니다",
        "의사선생님께 노티하겠습니다",
        "보고하겠습니다",
        "노티하겠습니다",
        "지금 보고하겠습니다",
        "지금 노티하겠습니다"
    ]
    if any(k in text for k in simple_report_keywords):
        return "report_intro"

    # ------------------------------------------------------------
    # 3. 처방 기반 중재
    # ------------------------------------------------------------
    intervention_keywords = [
        "산소를", "산소 연결", "산소 투여", "o2",
        "ntg", "니트로", "니트로글리세린",
        "아스피린", "투여하겠습니다", "드리겠습니다",
        "처방에 따라", "약물을 투여", "약을 드리겠습니다"
    ]
    if any(k in text for k in intervention_keywords):
        return "intervention"

    # ------------------------------------------------------------
    # 4. 중재 후 재사정
    # ------------------------------------------------------------
    reassess_keywords = [
        "통증은 지금", "지금 통증", "통증은 어느 정도", "통증은", "몇 점 정도",
        "숨쉬기는", "숨은", "호흡은", "호흡은 어떠세요", "숨쉬기는 좀 어떠세요",
        "어지럽", "불편한 증상", "더 불편", "다른 불편", "지금 좀 어떠세요",
        "상태를 다시 확인", "재사정"
    ]
    if st.session_state.intervention_done and any(k in text for k in reassess_keywords):
        return "reassessment"

    # ------------------------------------------------------------
    # 5. 중재 후 치료적 마무리
    # ------------------------------------------------------------
    closing_keywords = [
        "계속 상태를 관찰",
        "다시 통증이 심해지거나",
        "통증이 지속되면",
        "답답해지면",
        "답답해지면 바로 말씀",
        "바로 말씀해 주세요",
        "계속 관찰할 것",
        "계속 관찰할게요",
        "말씀해주세요",
        "알려주세요"
    ]
    if st.session_state.intervention_done and any(k in text for k in closing_keywords):
        return "closing_therapeutic"

    # ------------------------------------------------------------
    # 6. 활력징후 해석
    # ------------------------------------------------------------
    interpretation_keywords = [
        "혈압이 높", "맥박이 높", "혈압과 맥박이 높"
    ]
    if st.session_state.vitals_shown and any(k in text for k in interpretation_keywords):
        return "vitals_interpretation"

    # ------------------------------------------------------------
    # 7. 검사 시행 / 결과 확인
    # ------------------------------------------------------------
    exam_keywords = [
        "검사", "검사결과", "결과", "결과 확인", "결과 볼게요", "결과 보겠습니다", "결과 다시 보여",
        "심전도", "ekg", "ecg", "12유도", "12-lead",
        "혈액검사", "피검사", "채혈", "lab",
        "트로포닌", "troponin",
        "ck-mb", "ckmb"
    ]
    if any(k in text for k in exam_keywords):
        return "labs"

    # ------------------------------------------------------------
    # 8. 활력징후 확인
    # ------------------------------------------------------------
    vitals_keywords = [
        "활력징후", "바이탈", "v/s",
        "혈압", "맥박", "호흡수", "산소포화도", "spo2", "체온"
    ]
    if any(k in text for k in vitals_keywords):
        return "vitals"

    # ------------------------------------------------------------
    # 9. 병력 및 위험요인 사정
    # ------------------------------------------------------------
    history_keywords = [
        "기저질환", "질환", "평소", "약", "복용",
        "담배", "흡연", "알레르기", "병력"
    ]
    if any(k in text for k in history_keywords):
        return "history"

    # ------------------------------------------------------------
    # 10. 통증 및 증상 사정
    # ------------------------------------------------------------
    pain_keywords = [
        "어디", "어떻게", "언제", "통증", "퍼지", "방사",
        "숨이", "메스꺼움", "아프", "답답",
        "다른 곳", "다른 아픈곳", "다른 아픈 곳", "다른 증상"
    ]
    if any(k in text for k in pain_keywords):
        return "pain_assessment"

    # ------------------------------------------------------------
    # 11. 치료적 의사소통
    # ------------------------------------------------------------
    therapeutic_keywords = [
        "괜찮", "도와드리", "걱정하지", "불안", "안심", "옆에", "지금 바로", "무섭"
    ]
    if any(k in text for k in therapeutic_keywords):
        return "therapeutic"

    # ------------------------------------------------------------
    # 12. 그 외
    # ------------------------------------------------------------
    return "general"

# ------------------------------------------------------------
# 10. 응답 생성
# ------------------------------------------------------------
def get_response(user_text: str):
    category = classify_input(user_text)
    responses = []

    if category == "pain_assessment":
        st.session_state.checklist["초기 접촉 및 주호소 확인"] = True

        if ("어디" in user_text and "아프" in user_text) or ("가슴 어디가" in user_text):
            fact = "가슴 한가운데가 누가 꽉 쥐어짜는 것처럼 아프고 턱이랑 왼쪽 어깨까지 뻗친다."
        elif "다른 곳" in user_text or "다른 아픈곳" in user_text or "다른 아픈 곳" in user_text:
            fact = "턱이랑 왼쪽 어깨까지 뻗친다."
        elif "어떻게" in user_text:
            fact = "정말 꽉 조이는 느낌이고 너무 답답하다."
        elif "언제" in user_text:
            fact = "한 30분 전쯤 운전하다가 갑자기 시작됐다."
        elif "몇 점" in user_text or "통증 점수" in user_text:
            fact = "통증은 8점 정도로 매우 심하다."
        elif "퍼지" in user_text or "방사" in user_text:
            fact = "턱과 왼쪽 어깨까지 통증이 퍼진다."
        elif "다른 증상도" in user_text or "다른 증상" in user_text or "증상도" in user_text:
            fact = "숨이 차고 식은땀이 나며 너무 불안하다."
        elif "숨" in user_text or "메스꺼움" in user_text:
            fact = "숨이 차고 식은땀이 나며 너무 불안하다."
        else:
            fact = "가슴이 너무 아프고 답답하며 무섭다."

        responses.append(naturalize_with_openai(user_text, fact, tone="극심한 흉통과 불안 상태"))

    elif category == "vitals":
        st.session_state.vitals_shown = True
        st.session_state.checklist["활력징후 확인 시도"] = True

        responses.append(
            "[SYSTEM: 초기 활력징후]\n"
            f"혈압(BP): {VITAL_SIGNS['BP']}\n"
            f"맥박(HR): {VITAL_SIGNS['HR']}\n"
            f"호흡수(RR): {VITAL_SIGNS['RR']}\n"
            f"산소포화도(SpO₂): {VITAL_SIGNS['SpO2']}\n"
            f"체온(BT): {VITAL_SIGNS['BT']}"
        )

    elif category == "vitals_interpretation":
        responses.append("왜 이렇게 높게 나온거예요? 괜찮은 거 맞나요?")

    elif category == "family_history":
        st.session_state.checklist["병력 및 위험요인 사정"] = True
        fact = "아버지가 심장마비로 돌아가셨다."
        responses.append(naturalize_with_openai(user_text, fact, tone="불안하지만 질문에는 답하는 상태"))

    elif category == "history":
        st.session_state.checklist["병력 및 위험요인 사정"] = True

        if "알레르기" in user_text:
            fact = "알레르기는 없었던 것 같다."
        elif "질환" in user_text or "평소" in user_text:
            fact = "고혈압이 있고 혈압약을 먹고 있다."
        elif "약" in user_text or "복용" in user_text:
            fact = "혈압약은 먹고 있지만 약 이름은 잘 모른다."
        elif "담배" in user_text or "흡연" in user_text:
            fact = "담배를 오래 피웠고 하루에 한 갑 정도 핀다."
        else:
            fact = "고혈압이 있고 혈압약을 먹고 있다."

        responses.append(naturalize_with_openai(user_text, fact, tone="불안하지만 질문에는 답하는 상태"))

    elif category == "labs":
        st.session_state.labs_shown = True
        st.session_state.checklist["검사 시행 또는 결과 확인"] = True

        responses.append("네, 빨리 좀 해주세요.. 너무 무서워요.")
        responses.append(
            "[SYSTEM: EKG 결과]\n"
            f"- {LAB_RESULTS['ECG']}\n\n"
            "[SYSTEM: Lab 결과]\n"
            f"- Troponin I: {LAB_RESULTS['Troponin I']}\n"
            f"- CK-MB: {LAB_RESULTS['CK-MB']}"
        )

        if st.session_state.intervention_done:
            responses.append("아까보다는 조금 나아졌는데... 검사 결과는 많이 안 좋은 건가요?")

    elif category == "report_intro":
        st.session_state.checklist["SBAR 보고 수행"] = True
        responses.append("네, 의사에게 바로 보고해주세요.")

    elif category == "report_detail":
        st.session_state.order_shown = True
        st.session_state.checklist["SBAR 보고 수행"] = True

        responses.append(
            "[SYSTEM: 의사 처방 도착]\n"
            "1. O2 2L/min via Nasal Cannula\n"
            "2. NTG 0.6mg SL\n"
            "3. Aspirin 300mg PO\n"
            "4. 12-lead EKG Re-check"
        )

    elif category == "intervention":
        st.session_state.intervention_done = True
        st.session_state.checklist["처방 기반 중재 수행"] = True
        st.session_state.checklist["치료적 의사소통 사용"] = True

        responses.append("네, 선생님.. 빨리 좀 부탁드릴게요.. 너무 무서워요..")
        responses.append(
            "[SYSTEM: 중재 후 상태 변화]\n"
            "5분 후 환자는 통증이 감소하고 호흡이 다소 편해졌다고 표현한다."
        )
        responses.append("휴.. 아까보다는 좀 나아졌어요. 가슴 통증이 처음엔 8점 정도였는데 지금은 3점 정도예요... 숨쉬는 것도 조금 편해졌어요...")

    elif category == "reassessment":
        st.session_state.reassessment_done = True
        st.session_state.checklist["중재 후 재사정 수행"] = True

        if "통증" in user_text or "몇 점" in user_text:
            responses.append("3점 정도요.. 아까보단 훨씬 나아요...")
        elif "숨" in user_text or "호흡" in user_text:
            responses.append("조금 편해졌어요...")
        elif "어지럽" in user_text or "불편" in user_text:
            responses.append("지금은 좀 괜찮아요.. 그래도 무섭긴 해요...")
        else:
            responses.append("휴.. 아까보다는 좀 나아졌어요. 가슴 통증이 처음엔 8점 정도였는데 지금은 3점 정도예요... 숨쉬는 것도 조금 편해졌어요...")

    elif category == "closing_therapeutic":
        st.session_state.checklist["치료적 의사소통 사용"] = True
        responses.append("네.. 알겠습니다.. 선생님, 감사합니다.")

    elif category == "therapeutic":
        st.session_state.checklist["치료적 의사소통 사용"] = True
        responses.append("네.. 선생님이 그렇게 말씀해주시니까 조금 안심돼요...")

    else:
        responses.append("선생님.. 너무 아프고 불안해요... 도와주세요...")

    return responses

# ------------------------------------------------------------
# 11. 채팅 화면
# ------------------------------------------------------------
if st.session_state.started:
    st.subheader("💬 시뮬레이션 대화")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# ------------------------------------------------------------
# 12. 채팅 입력
# ------------------------------------------------------------
if st.session_state.started and not st.session_state.ended:
    user_input = st.chat_input("환자에게 질문하거나 간호중재를 입력하세요.")

    if user_input:
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        answers = get_response(user_input)

        for ans in answers:
            st.session_state.messages.append({
                "role": "assistant",
                "content": ans
            })

        st.rerun()

# ------------------------------------------------------------
# 13. 디브리핑
# ------------------------------------------------------------
if st.session_state.started:
    st.markdown("---")
    st.subheader("🧠 디브리핑")

    if not st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        if st.button("디브리핑 보기"):
            st.session_state.checklist["디브리핑 참여"] = True
            st.session_state.ended = True
            st.session_state.show_debriefing = True
            st.rerun()

    if st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        st.success("시뮬레이션이 종료되었습니다. 아래 질문을 바탕으로 성찰해보세요.")

        for i, q in enumerate(DEBRIEFING_QUESTIONS, start=1):
            st.write(f"{i}. {q}")

        st.markdown("### ✍ 디브리핑 답변 작성")

        st.text_area("1번 질문 답변", key="d1")
        st.text_area("2번 질문 답변", key="d2")
        st.text_area("3번 질문 답변", key="d3")
        st.text_area("4번 질문 답변", key="d4")

        all_filled = all([
            st.session_state.get("d1", "").strip(),
            st.session_state.get("d2", "").strip(),
            st.session_state.get("d3", "").strip(),
            st.session_state.get("d4", "").strip()
        ])

        if not all_filled:
            st.warning("디브리핑 답변 4개를 모두 작성한 후 종료할 수 있습니다.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("종료", disabled=not all_filled):
                st.session_state.debrief_submitted = True
                st.session_state.show_debriefing = False
                st.rerun()

        with col2:
            if st.button("디브리핑 취소"):
                st.session_state.show_debriefing = False
                st.session_state.ended = False
                st.rerun()

    if st.session_state.debrief_submitted:
        st.success("디브리핑이 완료되었습니다.")

        st.write("입력한 답변:")
        st.write(f"1번: {st.session_state.get('d1', '')}")
        st.write(f"2번: {st.session_state.get('d2', '')}")
        st.write(f"3번: {st.session_state.get('d3', '')}")
        st.write(f"4번: {st.session_state.get('d4', '')}")

        if st.button("첫 화면으로 돌아가기"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ------------------------------------------------------------
# 14. 하단 안내
# ------------------------------------------------------------
st.markdown("---")
st.caption("이 코드는 논문용 시뮬레이션 프로토타입 최종 예시입니다.")
