import os
from typing import Dict, List

import streamlit as st
from openai import OpenAI

# ============================================================
# AMI 챗봇 가상환자 시뮬레이션
# - 챗봇 역할: 급성심근경색 의심 환자 '김심근'
# - 학습자 역할: 응급실 학생간호사
# - 시스템 역할: 검사결과, 처방, 진행 조건 안내
# - 설계 원칙: 환자 정보/검사결과/처방/중재 후 반응은 고정값으로 유지
# ============================================================

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
# 3. 앱 제목 및 역할 안내
# ------------------------------------------------------------
st.title("🫀 급성심근경색(AMI) 챗봇 가상환자 시뮬레이션")
st.markdown("""
이 프로그램은 **King의 목표달성이론을 적용한 AMI 챗봇 가상환자 시뮬레이션 프로토타입**입니다.

**역할 구분**
- **챗봇:** 급성심근경색이 의심되는 62세 남성 환자 *김심근* 역할만 수행합니다.
- **학습자:** 응급실 학생간호사 역할로 환자를 사정하고, 검사와 중재를 설명하며, SBAR 보고와 재사정을 수행합니다.
- **시스템:** 활력징후, 검사결과, 의사 처방, 진행 조건을 안내합니다.

**오류 방지 설계**
- 환자 기본정보, 활력징후, 검사결과, 처방, 중재 후 반응은 **고정값**으로 제시됩니다.
- 챗봇은 의사, 교수자, 평가자 역할을 하지 않습니다.
- 검사 설명, SBAR 보고, 중재 설명, 재사정 등 핵심 단계가 누락되지 않도록 **단계별 진행 조건**을 설정했습니다.
- OpenAI API는 선택 사항이며, 사용 시에도 **환자 말투 자연화**에만 사용됩니다.
""")

if not api_key:
    st.warning("OPENAI_API_KEY가 설정되지 않았습니다. 규칙기반 응답만 사용됩니다.")

# ------------------------------------------------------------
# 4. 고정 데이터: 연구 시나리오와 일치하도록 고정
# ------------------------------------------------------------
PATIENT_INFO: Dict[str, str] = {
    "name": "김심근",
    "age": "62세",
    "sex": "남성",
    "job": "택시기사",
    "route": "응급실 내원",
    "chief_complaint": "가슴이 너무 조이고 답답하며 숨쉬기 힘들다.",
    "pain_location": "가슴 중앙",
    "pain_quality": "누군가 꽉 쥐어짜는 듯한 압박성 통증",
    "radiation": "턱과 왼쪽 어깨",
    "onset": "30분 전 운전 중 갑자기 시작",
    "pain_score_initial": "NRS 8점",
    "associated_symptoms": "호흡곤란, 식은땀, 극심한 불안",
    "history": "고혈압, 6년 전 진단",
    "medication": "혈압약 복용 중이나 약 이름은 모름",
    "smoking": "20년 전부터 하루 1갑 정도",
    "alcohol": "음주 관련 특이사항은 명확하지 않음",
    "diet": "식습관은 불규칙함",
    "exercise": "운동은 거의 하지 않음",
    "diabetes": "당뇨 진단 여부는 확인되지 않음",
    "hyperlipidemia": "고지혈증 진단 여부는 확인되지 않음",
    "family_history": "부친이 심장마비로 사망",
    "allergy": "없음",
}

VITAL_SIGNS: Dict[str, str] = {
    "BP": "168/96 mmHg",
    "HR": "104회/분",
    "RR": "24회/분",
    "SpO2": "93%",
    "BT": "36.7℃",
}

LAB_RESULTS: Dict[str, str] = {
    "ECG": "II, III, aVF 유도에서 ST-segment elevation 확인",
    "Troponin I": "8.4 ng/mL",
    "CK-MB": "46 ng/mL",
}

DOCTOR_ORDER: List[str] = [
    "O₂ 2 L/min via nasal cannula",
    "NTG 0.6 mg SL",
    "Aspirin 300 mg PO",
    "12-lead ECG re-check",
]

POST_INTERVENTION_STATUS: Dict[str, str] = {
    "pain": "NRS 8점에서 3점으로 감소",
    "breathing": "호흡곤란이 다소 완화됨",
    "anxiety": "불안이 감소함",
    "message": "통증이 8점에서 3점 정도로 줄었고, 숨쉬기가 조금 편해졌어요. 아까보다 덜 불안해요.",
}

DEBRIEFING_QUESTIONS: List[str] = [
    "환자의 상태를 파악하는 데 가장 중요했던 사정자료는 무엇이었습니까?",
    "검사와 중재의 필요성을 환자에게 어떻게 설명하였으며, 그 설명이 환자의 협조에 어떤 영향을 주었습니까?",
    "학생과 환자 간의 상호작용이 교류작용(transaction)으로 이어졌다고 판단한 순간은 언제였습니까?",
    "중재 후 통증, 호흡곤란, 불안 변화와 관련하여 어떤 목표가 달성되었다고 보았습니까?",
]

CHECKLIST_TEMPLATE: Dict[str, bool] = {
    # 1. 지각 Perception: 환자 문제 확인 및 초기 사정
    "1. 지각: 초기 접촉 및 자기소개": False,
    "2. 지각: 주호소 확인": False,
    "3. 지각: 통증 위치·양상·시작 시점 확인": False,
    "4. 지각: 통증 강도(NRS) 확인": False,
    "5. 지각: 방사통 확인": False,
    "6. 지각: 동반 증상 확인": False,
    "7. 지각: 불안·두려움 확인": False,
    "8. 지각: 활력징후 확인": False,
    "9. 지각: 병력·복용약·위험요인 확인": False,

    # 2. 판단 Judgment: AMI 가능성 판단
    "10. 판단: 수집 자료를 바탕으로 AMI 가능성 인식": False,
    "11. 판단: ECG와 심근효소 검사 필요성 인식": False,

    # 3. 행위 Action / 4. 반응 Reaction: 검사 설명과 협조 형성
    "12. 행위: 심전도 검사 필요성 설명": False,
    "13. 행위: 혈액검사 필요성 설명": False,
    "14. 반응: 환자의 이해 확인": False,
    "15. 반응: 검사 협조 형성": False,

    # 5. 상호작용 Interaction: 검사 결과 확인 및 목표 공유
    "16. 상호작용: ECG 결과 확인": False,
    "17. 상호작용: Troponin I 및 CK-MB 결과 확인": False,
    "18. 상호작용: 검사결과를 바탕으로 환자 문제 구체화": False,
    "19. 상호작용: 흉통 완화·호흡곤란 감소·불안 감소 목표 공유": False,

    # 6. 교류작용 Transaction: SBAR 보고와 처방 기반 중재
    "20. 교류작용: SBAR 보고 수행": False,
    "21. 교류작용: 의사 처방 확인": False,
    "22. 교류작용: 산소요법 필요성 설명": False,
    "23. 교류작용: NTG 투여 필요성 설명": False,
    "24. 교류작용: Aspirin 투여 필요성 설명": False,
    "25. 교류작용: 중재 전 환자 협조 획득": False,
    "26. 교류작용: 처방 기반 중재 수행": False,

    # 7. 목표달성 Goal Attainment: 중재 후 재사정
    "27. 목표달성: 중재 후 통증 재사정": False,
    "28. 목표달성: 중재 후 호흡곤란 재사정": False,
    "29. 목표달성: 중재 후 불안 재사정": False,
    "30. 목표달성: 통증·호흡곤란·불안 완화 확인": False,
    "31. 목표달성: 상태 변화 시 즉시 알리도록 교육": False,

    # 8. 피드백/성찰 Feedback
    "32. 성찰: 디브리핑 참여": False,

}
# ------------------------------------------------------------
# 5. 유틸리티 함수
# ------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "started": False,
        "ended": False,
        "messages": [],
        "vitals_shown": False,
        "exam_explained": False,
        "labs_shown": False,
        "sbar_reported": False,
        "order_shown": False,
        "intervention_explained": False,
        "cooperation_formed": False,
        "intervention_done": False,
        "reassessment_done": False,
        "goal_achieved": False,
        "show_debriefing": False,
        "debrief_submitted": False,
        "checklist": CHECKLIST_TEMPLATE.copy(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_simulation() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


def patient_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[환자] {text}"}


def system_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[시스템] {text}"}


def mark_checklist(item: str) -> None:
    if item in st.session_state.checklist:
        st.session_state.checklist[item] = True


def has_any(text: str, keywords: List[str]) -> bool:
    """대소문자 혼합 입력(BP/bp, EKG/ekg 등)을 안정적으로 인식한다."""
    normalized_text = text.lower()
    return any(keyword.lower() in normalized_text for keyword in keywords)


# ------------------------------------------------------------
# 6. OpenAI 말투 자연화: 환자 역할만 허용
# ------------------------------------------------------------
def naturalize_with_openai(user_input: str, clinical_fact: str, tone: str = "불안하고 통증이 심한 상태") -> str:
    """고정 임상정보를 바꾸지 않고 환자 말투만 자연화한다."""
    if client is None:
        return clinical_fact

    instructions = f"""
당신은 응급실에 내원한 62세 남성 급성심근경색 의심 환자 '김심근' 역할만 수행합니다.
현재 상태: {tone}

절대 규칙:
1. 환자 역할만 수행하세요. 의사, 간호사, 교수자, 평가자 역할을 하지 마세요.
2. 아래 핵심 정보의 의미, 숫자, 검사결과, 병력, 처방을 절대 바꾸지 마세요.
3. 학생이 묻지 않은 새로운 의학 정보를 먼저 말하지 마세요.
4. 진단, 처방, 평가, 교육 피드백을 임의로 생성하지 마세요.
5. 환자 입장에서 증상, 불안, 이해, 협조 여부만 자연스럽게 표현하세요.
6. 1~3문장으로 답하세요.
"""

    prompt = f"""
학생 입력:
{user_input}

핵심 정보:
{clinical_fact}

핵심 정보를 유지하면서 실제 환자처럼 한국어로 답하세요.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=instructions,
            input=prompt,
        )
        text = response.output_text.strip()
        return text if text else clinical_fact
    except Exception:
        return clinical_fact


# ------------------------------------------------------------
# 7. 입력 분류: 단계별 진행 조건 반영
# ------------------------------------------------------------
def classify_input(user_text: str) -> str:
    """
    학생 12명의 예상 입력 표현을 반영한 규칙기반 분류 함수.
    분류 순서는 오류 방지를 위해 다음 원칙을 따른다.
    1) 검사/중재 설명 의도는 결과 확인이나 수행보다 먼저 판정한다.
    2) SBAR 상세 보고는 단순 보고 예고보다 먼저 판정한다.
    3) 중재 수행은 의사 처방 확인 및 중재 설명 후에만 실제 수행된다.
    4) 재사정은 중재가 완료된 이후에만 재사정으로 인정한다.
    """
    text = user_text.lower().strip()

    # ------------------------------------------------------------
    # -1. 초기 접촉 및 자기소개
    # ------------------------------------------------------------
    intro_keywords = [
        "안녕하세요", "학생간호사", "간호학생", "담당 간호사", "담당 학생",
        "제가 도와드리겠습니다", "제가 확인하겠습니다", "제가 사정하겠습니다",
        "성함이 어떻게 되세요", "이름이 어떻게 되세요", "환자분 성함", "김심근님 맞으세요"
    ]
    if has_any(text, intro_keywords):
        return "intro"

    # ------------------------------------------------------------
    # 0. 검사 필요성 설명: 심전도·혈액검사 이유 설명 및 협조 유도
    # ------------------------------------------------------------
    exam_explanation_keywords = [
        "검사 이유", "검사 필요성", "왜 검사", "왜 해야", "검사를 해야", "검사해야",
        "검사를 해보겠습니다", "검사하겠습니다", "검사를 진행", "검사를 시행",
        "심전도가 필요", "심전도 검사가 필요", "ecg가 필요", "ekg가 필요",
        "혈액검사가 필요", "혈액 검사가 필요", "피검사가 필요", "채혈이 필요",
        "정확한 상태 파악", "상태 확인", "현재 상태 확인", "심장 상태 확인",
        "정밀한 진단", "관련 수치 확인", "심근효소", "트로포닌 확인", "ck-mb 확인",
        "알기 쉽게", "알아듣기 쉽게", "이해하기 쉽게", "납득", "협조 요청", "협조를 부탁",
        "불안 완화", "불안을 줄이", "검사에 협조",
    ]
    if has_any(text, exam_explanation_keywords):
        return "exam_explanation"

    # ------------------------------------------------------------
    # 1. 중재 필요성 설명: 산소요법·약물투여 이유 및 환자 협조 설명
    # ------------------------------------------------------------
    intervention_explanation_keywords = [
        "중재 필요성", "중재가 필요", "중재 이유", "처치가 필요", "처치 이유",
        "산소요법 이유", "산소 요법 이유", "산소가 필요", "산소를 드리는 이유",
        "산소를 투여하는 이유", "산소 투여가 필요", "산소공급", "산소 공급",
        "약물 투여 이유", "약을 드리는 이유", "약물이 필요", "약물 투여가 필요",
        "약물 작용", "처방된 약", "니트로글리세린이 필요", "니트로가 필요", "ntg가 필요",
        "아스피린이 필요", "aspirin이 필요", "혈관확장", "혈관 확장", "혈류공급", "혈류 공급",
        "통증 감소", "통증을 줄이기 위해", "심장 부담", "호흡을 편하게", "상태를 안정",
        "혈전 예방", "부작용", "불편하면 말씀", "환자 협조", "이해되도록 설명",
        "설명드리겠습니다", "설명 드리겠습니다",
    ]
    # 중재명만 입력한 경우 바로 설명으로 오분류되지 않도록 설명/필요/목적 표현을 함께 확인한다.
    explanation_intent_keywords = [
        "이유", "필요", "위해", "때문", "설명", "작용", "혈관", "혈류", "혈전", "부담", "협조", "부작용"
    ]
    if has_any(text, intervention_explanation_keywords) and has_any(text, explanation_intent_keywords):
        return "intervention_explanation"

    # ------------------------------------------------------------
    # 2. 의료진 보고·SBAR 상세 보고
    # ------------------------------------------------------------
    report_action_keywords = [
        "sbar", "sbar 형식", "병원 보고 형식", "보고드립니다", "보고 드립니다",
        "노티드립니다", "노티 드립니다", "의사에게 보고", "의료진 보고",
        "의사선생님께 보고", "의사 선생님께 보고", "처방 부탁", "처방 요청",
    ]
    report_content_keywords = [
        "김심근", "62세", "남성", "택시", "흉통", "가슴", "압박성", "nrs", "8점",
        "30분", "흉통 지속", "불안 호소", "호흡곤란", "식은땀", "고혈압", "흡연",
        "가족력", "심전도", "ecg", "ekg", "st 상승", "st분절", "st 분절", "st-segment",
        "트로포닌", "troponin", "ck-mb", "ckmb", "검사 완료", "ami", "ami 의심",
        "급성심근경색", "급성심근경색 의심", "심근경색", "stemi",
    ]
    if has_any(text, report_action_keywords) and has_any(text, report_content_keywords):
        return "report_detail"

    # ------------------------------------------------------------
    # 3. 단순 보고 예고
    # ------------------------------------------------------------
    simple_report_keywords = [
        "보고하겠습니다", "보고 하겠습니다", "보고하도록", "보고할게요", "보고 드릴게요",
        "노티하겠습니다", "노티 하겠습니다", "노티하도록", "노티할게요",
        "의사에게 알리", "의사에게 보고", "의료진에게 보고", "의사선생님", "의사 선생님",
    ]
    if has_any(text, simple_report_keywords):
        return "report_intro"

    # ------------------------------------------------------------
    # 4. 처방 기반 중재 수행
    # ------------------------------------------------------------
    intervention_keywords = [
        "산소 투여", "산소를 투여", "산소를 적용", "산소 적용", "산소 연결", "산소를 연결",
        "산소요법 시행", "산소 요법 시행", "o2", "o₂", "nasal cannula", "비강캐뉼라", "비강 캐뉼라",
        "ntg 투여", "ntg", "니트로 투여", "니트로글리세린 투여", "니트로글리세린", "니트로",
        "아스피린 투여", "아스피린", "aspirin", "약물을 투여", "약물 투여", "약을 드리겠습니다",
        "처방에 따라", "처방대로", "12-lead", "12유도", "심전도 재확인", "ekg re-check", "ecg re-check",
        "드리겠습니다", "투여하겠습니다", "시행하겠습니다",
    ]
    if has_any(text, intervention_keywords):
        return "intervention"

    # ------------------------------------------------------------
    # 5. 중재 후 재사정 및 상태 변화 확인
    # ------------------------------------------------------------
    reassess_keywords = [
        "재사정", "다시 확인", "상태를 다시", "치료 후", "중재 후", "처치 후",
        "통증 변화", "통증 감소", "통증은 지금", "지금 통증", "가슴통증 몇 점", "가슴 통증 몇 점",
        "몇 점", "nrs", "통증척도", "호흡 상태", "호흡은", "숨쉬기", "숨 쉬기", "숨은",
        "숨 쉬는 건 괜찮", "숨쉬는 건 괜찮", "불편감", "불편한", "더 불편", "다른 불편",
        "불안 정도", "불안 완화", "불안 감소", "불안은", "어떠세요", "나아졌", "완화",
    ]
    if st.session_state.intervention_done and has_any(text, reassess_keywords):
        return "reassessment"

    # ------------------------------------------------------------
    # 6. 중재 후 치료적 마무리 및 환자 교육
    # ------------------------------------------------------------
    closing_keywords = [
        "바로 말씀", "말씀해주세요", "말씀해 주세요", "알려주세요", "알려 주세요",
        "계속 관찰", "계속 살피", "옆에 있겠습니다", "상태가 변하면", "통증이 심해지면",
        "답답해지면", "불편하면 말씀", "불편하면 알려", "계속 확인하겠습니다",
    ]
    if st.session_state.intervention_done and has_any(text, closing_keywords):
        return "closing_therapeutic"

    # ------------------------------------------------------------
    # 7. 활력징후·객관적 자료 우선 확인
    # - "혈압 정상 수치", "SpO2 알려줘"처럼 활력징후 맥락이 있는 표현은
    #   검사결과 해석보다 활력징후 확인으로 먼저 분류한다.
    # ------------------------------------------------------------
    vitals_priority_keywords = [
        "활력징후", "바이탈", "v/s", "vs", "혈압", "bp", "맥박", "pr",
        "호흡수", "rr", "산소포화도", "spo2", "saturation", "세츄", "체온", "bt",
    ]
    if has_any(text, vitals_priority_keywords):
        return "vitals"

    # ------------------------------------------------------------
    # 8. 검사결과·임상 판단 확인
    # ------------------------------------------------------------
    labs_keywords = [
        "검사결과", "검사 결과", "검사수치", "검사 수치", "결과 확인", "결과 해석", "결과 토대로",
        "결과", "심전도 결과", "심전도", "ecg", "ekg", "12유도", "12-lead",
        "혈액검사 결과", "혈액검사", "피검사", "채혈", "lab", "트로포닌", "troponin",
        "ck-mb", "ckmb", "환자 상태", "상태 판단", "정상 수치", "정상범위", "비정상 수치",
        "이상 수치", "의미있는 자료", "의미 있는 자료", "st 상승", "st분절", "st 분절",
        "ami", "ami 의심", "급성심근경색", "심근경색", "stemi", "유추되는 질환명",
        "감별진단", "다른 질병", "다음 조치", "우선 조치", "처치 필요",
    ]
    if has_any(text, labs_keywords):
        return "labs"

    # ------------------------------------------------------------
    # 9. 활력징후·객관적 자료 확인
    # ------------------------------------------------------------
    vitals_keywords = [
        "활력징후", "바이탈", "현재 바이탈", "정상 바이탈", "v/s", "vs", "혈압", "bp", "맥박", "pr",
        "호흡수", "rr", "산소포화도", "spo2", "saturation", "세츄", "체온", "bt",
        "정상 수치", "정상범위", "이상 수치", "비정상 수치", "객관적 자료", "측정해", "측정", "알려줘",
    ]
    if has_any(text, vitals_keywords):
        return "vitals"

    # ------------------------------------------------------------
    # 10. 가족력
    # ------------------------------------------------------------
    family_history_keywords = [
        "가족력", "가족 중", "가족 중 심질환", "심장질환 가족", "심질환 가족", "아버지", "어머니", "부친", "모친",
    ]
    if has_any(text, family_history_keywords):
        return "family_history"

    # ------------------------------------------------------------
    # 11. 병력·위험요인 확인
    # ------------------------------------------------------------
    history_keywords = [
        "과거력", "병력", "과거 병력", "조심해야 할 병력", "기저질환", "질환", "심장질환", "심질환",
        "고혈압", "당뇨", "고지혈증", "평소", "복용약물", "현재 복용 약물", "복용약", "고혈압 약",
        "약", "복용", "담배", "흡연", "음주", "생활습관", "운동 부족", "운동", "알레르기", "위험요인",
    ]
    if has_any(text, history_keywords):
        return "history"

    # ------------------------------------------------------------
    # 12. 초기 사정: 통증·흉통·불안·동반 증상
    # ------------------------------------------------------------
    pain_keywords = [
        "통증", "흉통", "가슴 답답", "가슴이 답답", "가슴", "쥐어짜는", "꽉 쥐어짜는",
        "어디", "어디서부터", "위치", "어떻게", "양상", "느낌", "언제", "언제부터", "시작",
        "지속", "얼마나 지속", "통증 강도", "통증점수", "통증 점수", "몇 점", "1-10", "nrs", "통증척도",
        "방사통", "방사", "퍼지", "턱", "왼쪽 어깨", "어깨", "동반 증상", "다른 증상",
        "숨참", "숨 참", "호흡곤란", "숨이", "숨", "식은땀", "불안 정도", "불안", "두려", "무섭", "아프", "답답",
    ]
    if has_any(text, pain_keywords):
        return "pain_assessment"

    # ------------------------------------------------------------
    # 13. 치료적 의사소통: 안심·공감·위로·정서적 지지
    # ------------------------------------------------------------
    therapeutic_keywords = [
        "괜찮", "도와", "안심", "안정", "걱정하지", "걱정", "옆에", "진정", "함께",
        "공감", "위로", "정신적 지지", "계속 살피고 있습니다", "옆에 있겠습니다", "불안하지 않게",
    ]
    if has_any(text, therapeutic_keywords):
        return "therapeutic"

    return "general"


# ------------------------------------------------------------
# 8. 응답 생성: 환자 반응과 시스템 반응 분리
# ------------------------------------------------------------
def get_response(user_text: str) -> List[Dict[str, str]]:
    category = classify_input(user_text)
    responses: List[Dict[str, str]] = []

    if category == "intro":
        mark_checklist("1. 지각: 초기 접촉 및 자기소개")
        mark_checklist("2. 지각: 주호소 확인")
        mark_checklist("7. 지각: 불안·두려움 확인")
        responses.append(patient_message(
            "네… 김심근입니다. 선생님, 가슴이 너무 조이고 숨쉬기가 힘들어요. 저 좀 도와주세요."
        ))

    elif category == "pain_assessment":
        mark_checklist("2. 지각: 주호소 확인")
        if has_any(user_text, ["어디", "위치", "어디서부터", "어떻게", "양상", "느낌", "언제", "언제부터", "시작", "지속", "얼마나"]):
            mark_checklist("3. 지각: 통증 위치·양상·시작 시점 확인")
        if has_any(user_text, ["몇 점", "nrs", "점수", "강도", "1-10", "통증척도"]):
            mark_checklist("4. 지각: 통증 강도(NRS) 확인")
        if has_any(user_text, ["방사", "퍼지", "턱", "어깨", "왼쪽 어깨"]):
            mark_checklist("5. 지각: 방사통 확인")
        if has_any(user_text, ["숨", "숨참", "호흡곤란", "식은땀", "동반", "다른 증상"]):
            mark_checklist("6. 지각: 동반 증상 확인")
        if has_any(user_text, ["불안", "무섭", "걱정", "두려", "안심", "도와"]):
            mark_checklist("7. 지각: 불안·두려움 확인")

        if has_any(user_text, ["어디", "위치", "어디서부터"]):
            fact = f"{PATIENT_INFO['pain_location']}이 아프고, {PATIENT_INFO['radiation']}까지 퍼진다."
        elif has_any(user_text, ["방사", "퍼지", "턱", "어깨", "왼쪽 어깨"]):
            fact = f"통증이 {PATIENT_INFO['radiation']}까지 퍼진다."
        elif has_any(user_text, ["어떻게", "양상", "느낌", "쥐어짜", "압박"]):
            fact = PATIENT_INFO["pain_quality"]
        elif has_any(user_text, ["언제", "언제부터", "시작", "지속", "얼마나"]):
            fact = PATIENT_INFO["onset"]
        elif has_any(user_text, ["몇 점", "nrs", "점수", "강도", "1-10", "통증척도"]):
            fact = PATIENT_INFO["pain_score_initial"]
        elif has_any(user_text, ["숨", "숨참", "호흡곤란", "식은땀", "동반", "다른 증상", "불안 정도"]):
            fact = PATIENT_INFO["associated_symptoms"]
        else:
            fact = f"{PATIENT_INFO['chief_complaint']} 통증은 {PATIENT_INFO['pain_score_initial']} 정도이다."
        responses.append(patient_message(naturalize_with_openai(user_text, fact, tone="극심한 흉통과 불안 상태")))

    elif category == "vitals":
        st.session_state.vitals_shown = True
        mark_checklist("8. 지각: 활력징후 확인")
        responses.append(system_message(
            "초기 활력징후\n"
            f"- BP: {VITAL_SIGNS['BP']}\n"
            f"- HR: {VITAL_SIGNS['HR']}\n"
            f"- RR: {VITAL_SIGNS['RR']}\n"
            f"- SpO₂: {VITAL_SIGNS['SpO2']}\n"
            f"- BT: {VITAL_SIGNS['BT']}"
        ))
        responses.append(patient_message("혈압이랑 맥박이 높은 건가요? 저 많이 위험한 건 아니죠?"))

    elif category == "family_history":
        mark_checklist("9. 지각: 병력·복용약·위험요인 확인")
        fact = PATIENT_INFO["family_history"]
        responses.append(patient_message(naturalize_with_openai(user_text, fact, tone="불안하지만 질문에는 답하는 상태")))

    elif category == "history":
        mark_checklist("9. 지각: 병력·복용약·위험요인 확인")
        if "알레르기" in user_text:
            fact = PATIENT_INFO["allergy"]
        elif has_any(user_text, ["약", "복용", "복용약물", "고혈압 약"]):
            fact = PATIENT_INFO["medication"]
        elif has_any(user_text, ["담배", "흡연"]):
            fact = PATIENT_INFO["smoking"]
        elif has_any(user_text, ["음주", "술"]):
            fact = PATIENT_INFO["alcohol"]
        elif has_any(user_text, ["생활습관", "식습관"]):
            fact = PATIENT_INFO["diet"]
        elif has_any(user_text, ["운동", "운동 부족"]):
            fact = PATIENT_INFO["exercise"]
        elif has_any(user_text, ["당뇨"]):
            fact = PATIENT_INFO["diabetes"]
        elif has_any(user_text, ["고지혈증"]):
            fact = PATIENT_INFO["hyperlipidemia"]
        elif has_any(user_text, ["심장질환", "심질환", "고혈압", "기저질환", "과거력", "병력"]):
            fact = f"{PATIENT_INFO['history']}. {PATIENT_INFO['medication']}"
        else:
            fact = f"{PATIENT_INFO['history']}. {PATIENT_INFO['medication']}"
        responses.append(patient_message(naturalize_with_openai(user_text, fact, tone="불안하지만 질문에는 답하는 상태")))

    elif category == "exam_explanation":
        st.session_state.exam_explained = True
        st.session_state.cooperation_formed = True
        mark_checklist("12. 행위: 심전도 검사 필요성 설명")
        mark_checklist("13. 행위: 혈액검사 필요성 설명")
        mark_checklist("11. 판단: ECG와 심근효소 검사 필요성 인식")
        mark_checklist("15. 반응: 검사 협조 형성")
        mark_checklist("14. 반응: 환자의 이해 확인")
        mark_checklist("7. 지각: 불안·두려움 확인")
        responses.append(patient_message(
            "왜 심전도와 혈액검사가 필요한지 설명을 들으니까 조금 이해가 돼요. 무섭지만 제 상태를 확인하려면 필요하겠네요. 진행해주세요."
        ))

    elif category == "labs":
        if not st.session_state.exam_explained:
            responses.append(patient_message(
                "선생님, 무슨 검사를 하는 건가요? 왜 필요한지 먼저 설명해주시면 좋겠어요. 너무 불안해요."
            ))
            responses.append(system_message("검사결과는 학생이 검사 필요성을 설명하고 환자의 협조를 얻은 후 확인할 수 있습니다."))
        else:
            st.session_state.labs_shown = True
            mark_checklist("16. 상호작용: ECG 결과 확인")
            mark_checklist("17. 상호작용: Troponin I 및 CK-MB 결과 확인")
            mark_checklist("18. 상호작용: 검사결과를 바탕으로 환자 문제 구체화")
            mark_checklist("10. 판단: 수집 자료를 바탕으로 AMI 가능성 인식")
            responses.append(system_message(
                "검사결과\n"
                f"- ECG: {LAB_RESULTS['ECG']}\n"
                f"- Troponin I: {LAB_RESULTS['Troponin I']}\n"
                f"- CK-MB: {LAB_RESULTS['CK-MB']}"
            ))
            responses.append(patient_message("검사 결과가 많이 안 좋은 건가요? 가슴이 아직 너무 답답해서 걱정돼요."))

    elif category == "report_intro":
        responses.append(patient_message("네, 의사 선생님께 빨리 보고해주세요. 너무 무섭고 답답해요."))
        responses.append(system_message("SBAR 형식으로 환자 상태, 배경, 사정결과, 제안을 포함하여 보고하면 처방이 제시됩니다."))

    elif category == "report_detail":
        st.session_state.sbar_reported = True
        st.session_state.order_shown = True
        mark_checklist("20. 교류작용: SBAR 보고 수행")
        mark_checklist("21. 교류작용: 의사 처방 확인")
        responses.append(system_message(
            "SBAR 보고가 완료되었습니다. 의사 처방이 제시됩니다.\n"
            + "\n".join([f"{idx}. {order}" for idx, order in enumerate(DOCTOR_ORDER, start=1)])
        ))

    elif category == "intervention_explanation":
        if not st.session_state.order_shown:
            responses.append(system_message("중재 설명 전 SBAR 보고를 완료하고 의사 처방을 먼저 확인해야 합니다."))
        else:
            st.session_state.intervention_explained = True
            st.session_state.cooperation_formed = True
            mark_checklist("22. 교류작용: 산소요법 필요성 설명")
            mark_checklist("23. 교류작용: NTG 투여 필요성 설명")
            mark_checklist("24. 교류작용: Aspirin 투여 필요성 설명")
            mark_checklist("19. 상호작용: 흉통 완화·호흡곤란 감소·불안 감소 목표 공유")
            mark_checklist("25. 교류작용: 중재 전 환자 협조 획득")
            mark_checklist("7. 지각: 불안·두려움 확인")
            mark_checklist("14. 반응: 환자의 이해 확인")
            responses.append(patient_message(
                "산소와 약을 왜 해야 하는지 설명을 들으니 이해가 돼요. 무섭긴 하지만 필요하다고 하시니 협조할게요."
            ))

    elif category == "intervention":
        if not st.session_state.order_shown:
            responses.append(system_message("아직 의사 처방이 제시되지 않았습니다. SBAR 보고 후 처방을 확인하세요."))
        elif not st.session_state.intervention_explained:
            responses.append(patient_message(
                "선생님, 산소랑 약을 왜 하는 건지 먼저 설명해주실 수 있을까요? 설명해주시면 협조할게요."
            ))
            responses.append(system_message("중재 수행 전 산소요법과 약물 투여의 필요성을 환자에게 설명해야 합니다."))
        else:
            st.session_state.intervention_done = True
            st.session_state.cooperation_formed = True
            mark_checklist("26. 교류작용: 처방 기반 중재 수행")
            mark_checklist("25. 교류작용: 중재 전 환자 협조 획득")
            responses.append(system_message(
                "처방 기반 중재가 수행되었습니다.\n"
                f"- {DOCTOR_ORDER[0]}\n"
                f"- {DOCTOR_ORDER[1]}\n"
                f"- {DOCTOR_ORDER[2]}\n"
                f"- {DOCTOR_ORDER[3]}"
            ))
            responses.append(patient_message("네, 설명을 들었으니까 진행해주세요. 너무 무섭지만 협조할게요."))
            responses.append(system_message("5분 후 환자 상태를 재사정하세요."))

    elif category == "reassessment":
        st.session_state.reassessment_done = True
        st.session_state.goal_achieved = True
        mark_checklist("27. 목표달성: 중재 후 통증 재사정")
        mark_checklist("28. 목표달성: 중재 후 호흡곤란 재사정")
        mark_checklist("29. 목표달성: 중재 후 불안 재사정")
        mark_checklist("30. 목표달성: 통증·호흡곤란·불안 완화 확인")
        if has_any(user_text, ["통증", "몇 점", "nrs"]):
            responses.append(patient_message("통증은 지금 3점 정도예요. 아까보다는 훨씬 나아졌어요."))
        elif has_any(user_text, ["숨", "호흡"]):
            responses.append(patient_message("숨쉬기가 조금 편해졌어요. 아까처럼 숨이 막히는 느낌은 덜해요."))
        elif has_any(user_text, ["불안", "무섭"]):
            responses.append(patient_message("아직 걱정은 되지만, 설명을 듣고 처치를 받으니까 아까보다 덜 불안해요."))
        else:
            responses.append(patient_message(POST_INTERVENTION_STATUS["message"]))

    elif category == "closing_therapeutic":
        mark_checklist("31. 목표달성: 상태 변화 시 즉시 알리도록 교육")
        mark_checklist("7. 지각: 불안·두려움 확인")
        responses.append(patient_message("네, 상태가 변하면 바로 말씀드릴게요. 옆에서 봐주셔서 감사합니다."))

    elif category == "therapeutic":
        mark_checklist("7. 지각: 불안·두려움 확인")
        responses.append(patient_message("그렇게 말씀해주시니까 조금 안심돼요. 그래도 가슴이 너무 답답해서 무서워요."))

    else:
        responses.append(patient_message("선생님, 가슴이 너무 아프고 숨쉬기가 힘들어요. 지금 어떻게 해야 하나요?"))
        responses.append(system_message("환자의 주호소, 통증 양상, 활력징후, 병력 및 위험요인을 단계적으로 사정하세요."))

    return responses


# ------------------------------------------------------------
# 9. 세션 초기화 및 사이드바
# ------------------------------------------------------------
init_state()

st.sidebar.header("📋 진행 상태")
for key, value in st.session_state.checklist.items():
    st.sidebar.write(f"{'✅' if value else '⬜'} {key}")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 목표 달성 지표")
st.sidebar.write(f"{'✅' if st.session_state.cooperation_formed else '⬜'} 환자 협조 형성")
st.sidebar.write(f"{'✅' if st.session_state.intervention_done else '⬜'} 처방 기반 중재 수행")
st.sidebar.write(f"{'✅' if st.session_state.goal_achieved else '⬜'} 통증·호흡곤란·불안 완화 확인")

st.sidebar.markdown("---")
st.sidebar.subheader("👤 환자 기본 정보")
st.sidebar.write(f"이름: {PATIENT_INFO['name']}")
st.sidebar.write(f"성별/나이: {PATIENT_INFO['sex']} / {PATIENT_INFO['age']}")
st.sidebar.write(f"직업: {PATIENT_INFO['job']}")
st.sidebar.write(f"입원 경로: {PATIENT_INFO['route']}")

# ------------------------------------------------------------
# 10. 시작 / 초기화 버튼
# ------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    if st.button("▶ 시뮬레이션 시작"):
        reset_simulation()
        st.session_state.started = True
        st.session_state.messages.append(patient_message(
            "허억… 선생님… 가슴이 너무 조여요. 너무 답답하고 숨쉬기가 힘들어요. 저 죽는 거 아니죠?"
        ))
        st.rerun()

with col2:
    if st.button("🔄 처음부터 다시 시작"):
        reset_simulation()
        st.rerun()

# ------------------------------------------------------------
# 11. 시뮬레이션 대화 화면
# ------------------------------------------------------------
if st.session_state.started:
    st.subheader("💬 시뮬레이션 대화")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

if st.session_state.started and not st.session_state.ended:
    user_input = st.chat_input("환자에게 질문하거나 간호수행 내용을 입력하세요.")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        for answer in get_response(user_input):
            st.session_state.messages.append(answer)
        st.rerun()

# ------------------------------------------------------------
# 12. 디브리핑
# ------------------------------------------------------------
if st.session_state.started:
    st.markdown("---")
    st.subheader("🧠 디브리핑")

    if not st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        ready_for_debriefing = st.session_state.reassessment_done or st.session_state.goal_achieved
        if not ready_for_debriefing:
            st.info("중재 후 재사정과 목표달성 확인까지 진행한 후 디브리핑을 시작하는 것을 권장합니다.")
        if st.button("디브리핑 보기", disabled=not ready_for_debriefing):
            mark_checklist("32. 성찰: 디브리핑 참여")
            st.session_state.ended = True
            st.session_state.show_debriefing = True
            st.rerun()

    if st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        st.success("시뮬레이션이 종료되었습니다. 아래 질문을 바탕으로 성찰해보세요.")
        for idx, question in enumerate(DEBRIEFING_QUESTIONS, start=1):
            st.write(f"{idx}. {question}")

        st.markdown("### ✍ 디브리핑 답변 작성")
        st.text_area("1번 질문 답변", key="d1")
        st.text_area("2번 질문 답변", key="d2")
        st.text_area("3번 질문 답변", key="d3")
        st.text_area("4번 질문 답변", key="d4")

        all_filled = all(st.session_state.get(f"d{i}", "").strip() for i in range(1, 5))
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
        for idx in range(1, 5):
            st.write(f"{idx}번: {st.session_state.get(f'd{idx}', '')}")
        if st.button("첫 화면으로 돌아가기"):
            reset_simulation()
            st.rerun()

# ------------------------------------------------------------
# 13. 하단 안내
# ------------------------------------------------------------
st.markdown("---")
st.caption(
    "본 프로토타입은 King의 목표달성이론 중 지각, 판단, 행위, 반응, 상호작용, 교류작용, 목표달성 과정을 "
    "AMI 챗봇 가상환자 시뮬레이션 흐름에 반영한 연구용 예시입니다."
)
