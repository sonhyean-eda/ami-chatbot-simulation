import os
from html import escape, unescape
import re
from typing import Dict, List, Tuple

import streamlit as st
from openai import OpenAI

# ============================================================
# AMI 챗봇 가상환자 프로그램
# - 챗봇 역할: 급성심근경색 의심 환자 '김심근'
# - 학습자 역할: 응급실 학생간호사
# - 시스템 역할: 활력징후, 검사결과, 의사 처방 제시
# - 설계 원칙:
#   1) 환자 정보/검사결과/처방/중재 후 반응은 고정값으로 유지
#   2) King 목표달성이론 흐름을 한 방향으로 반영
#   3) 챗봇은 환자 역할만 수행하고 의사/교수자/평가자 역할을 하지 않음
#   4) 진행 상태는 내부 체크리스트로만 관리하고, 화면의 시스템 정보는 객관적 임상자료로 제한함
# ============================================================

# ------------------------------------------------------------
# 1. 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="AMI 챗봇 가상환자 프로그램",
    page_icon="🫀",
    layout="wide"
)

# ------------------------------------------------------------
# 2. OpenAI 클라이언트 준비
# ------------------------------------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# ------------------------------------------------------------
# 3. 앱 제목, 프로그램 설명 토글 및 상황 제시
# ------------------------------------------------------------
st.title("🫀 급성심근경색(AMI) 챗봇 가상환자 프로그램")

st.markdown("""
<style>
/* 안내 문구는 왼쪽 정렬로 유지하고 글자만 보기 좋게 조정 */
.chat-compact-guide {
    margin: 0 0 6px 0;
    font-size: 1.0rem;
    color: #475569;
}

/* 채팅 입력창은 기본 폭을 유지 */
div[data-testid="stChatInput"] {
    margin-left: 0;
    margin-right: 0;
}

/* caption은 너무 작지 않게 유지 */
.stCaptionContainer, div[data-testid="stCaptionContainer"] {
    font-size: 0.95rem;
}

/* 정보 박스도 기본 폭 유지 */
div[data-testid="stAlert"] {
    font-size: 1.02rem;
}


/* 채팅창 메시지와 입력창 글자 크기 확대 */
div[data-testid="stChatInput"] textarea {
    font-size: 1.15rem !important;
    line-height: 1.5 !important;
}

.stTextArea textarea, .stTextInput input {
    font-size: 1.08rem !important;
    line-height: 1.5 !important;
}

button, .stButton button {
    font-size: 1.02rem !important;
}
</style>
""", unsafe_allow_html=True)

# 사이드바에서 클릭했을 때만 큰 화면에 프로그램 설명이 나타나도록 설정
show_program_description = st.sidebar.toggle("📘 프로그램 설명 보기", value=False)

PROGRAM_DESCRIPTION = """
이 프로그램은 **King의 목표달성이론을 적용한 AMI 챗봇 가상환자 프로토타입**입니다.

**역할 구분**
- **챗봇:** 급성심근경색이 의심되는 62세 남성 환자 *김심근* 역할만 수행합니다.
- **학습자:** 응급실 학생간호사 역할로 환자를 사정하고, 검사와 중재를 설명하며, SBAR 보고와 재사정을 수행합니다.
- **시스템:** 환자확인 정보, 활력징후, 검사결과, 의사 처방만 제시합니다.

**오류 방지 설계**
- 환자 기본정보, 활력징후, 검사결과, 의사 처방, 중재 후 반응은 **고정값**으로 제시됩니다.
- 챗봇은 **의사, 교수자, 평가자 역할을 하지 않으며**, 급성심근경색이 의심되는 환자 역할만 수행합니다.
- 환자확인 정보, 활력징후, 검사결과, 의사 처방은 환자 응답이 아니라 **시스템 정보**로만 제시됩니다.
- 학생이 한 문장으로 완성된 답변을 입력하지 않아도, 짧은 발화를 단계별로 입력하면 프로그램이 이를 **누적 인식**하도록 구성했습니다.
- 검사 설명 단계, 상호작용 단계, 중재 설명 단계에서 핵심 항목이 2회 이상 충족되지 않을 경우, 정답이 아닌 **누락 항목 중심의 표준화된 힌트**를 제공합니다.
- 중재 수행 이후에는 재사정 단계로 고정하여 중재 후 고정 반응이 일관되게 제시되도록 합니다.
- OpenAI API는 선택 사항이며, 사용 시에도 **환자 말투 자연화**에만 사용됩니다. 환자 정보, 검사결과, 처방, 중재 후 반응은 임의로 변경되지 않습니다.

**King 목표달성이론 흐름 반영**
- 프로그램은 **지각 → 판단 → 행위 → 반응 → 상호작용 → 교류작용 → 목표달성** 순서로 한 방향으로 진행됩니다.
- 지각 단계는 **초기 접촉 및 주호소 확인 → 통증 및 동반 증상 사정 → 활력징후 확인 → 병력 및 위험요인 사정**으로 구성됩니다.
- 검사결과 확인은 판단 단계로 되돌아가는 것이 아니라, 이후 **상호작용 단계에서 환자 문제를 구체화하기 위한 자료**로 사용됩니다.
- 상호작용 단계에는 **환자 문제 확인, 간호목표 공유, 목표달성 방법 설명, 환자의 이해와 참여 확인**이 포함됩니다.
- 교류작용 단계에는 **SBAR 보고, 처방 확인, 중재 설명, 중재 수행**이 포함됩니다.

**학생 발화 인식 방식**
- 학생이 긴 문장을 한 번에 입력하지 않아도 됩니다.
- 검사 설명, 상호작용, 중재 설명은 **짧은 문장들을 누적하여 인식**합니다.
"""

PROGRESS_DESCRIPTION = """
📌 **진행상태 완료 기준 안내**

- 진행상태는 학습자의 수행 과정을 돕기 위한 체크리스트입니다.
- 모든 항목을 한 번에 완벽하게 작성해야 다음 단계로 넘어가는 것은 아닙니다.
- 학생이 입력한 질문과 설명은 단계별로 누적 인식되며, 각 단계의 핵심 수행 내용이 충족되면 해당 단계가 완료로 표시됩니다.
- 검사 설명 단계, 상호작용 단계, 중재 설명 단계는 한 번의 입력에서 여러 핵심 항목을 동시에 인식하며, 2회 이상 막히면 누락 항목 중심 힌트를 제공합니다.
- 중재 수행 후에는 통증·호흡곤란·불안 관련 입력이 초기 사정으로 되돌아가지 않고 재사정 단계로 우선 분류됩니다.
- 다만 **검사결과 확인, SBAR 보고, 의사 처방 확인, 중재 수행, 디브리핑**은 정해진 순서에 따라 진행됩니다.
- 환자 대화창 안에서도 현재 단계가 함께 표시되어, 어느 단계의 응답인지 바로 확인할 수 있습니다.
- 각 단계의 해야 할 일과 완료 기준은 왼쪽 진행상태를 클릭하여 확인할 수 있습니다.
"""

if show_program_description:
    st.subheader("📘 프로그램 설명")
    st.markdown(PROGRAM_DESCRIPTION)
    st.info(PROGRESS_DESCRIPTION)
else:
    # 첫 화면은 기존처럼 시나리오 상황을 중심으로 제시
    st.subheader("🚨 시나리오 상황")

    st.markdown("""
    ### 👤 환자 기본정보

    | 항목 | 내용 |
    |---|---|
    | 이름 | 김심근 |
    | 등록번호 | 2500611 |
    | 성별/나이 | 남성 / 62세 |
    | 직업 | 택시기사 |
    | 내원 경로 | 응급실 내원 |

    ---

    ### 🏥 현재 상황

    환자 **김심근**은 62세 남성 택시기사로, 운전 중 갑자기 발생한 흉통으로 응급실에 내원하였다.

    환자는 매우 불안한 표정으로 다음과 같이 호소하고 있다.

    > “가슴이 너무 조이고 답답해요.”  
    > “숨쉬기가 힘들어요.”  
    > “저 죽는 거 아니죠?”

    현재 환자는 **가슴 중앙의 압박성 통증**, **턱, 왼쪽 어깨, 등으로 퍼지는 방사통 및 등 통증**, 
    **식은땀**, **호흡곤란**, **극심한 불안**을 호소하고 있다.

    당신은 **응급실 학생간호사**로서 환자의 상태를 사정하고, 필요한 검사와 처치를 설명하며,
    의사에게 SBAR로 보고하고, 처방에 따른 간호중재와 중재 후 재사정을 수행해야 한다.
    """)
if not api_key:
    st.warning("OPENAI_API_KEY가 설정되지 않았습니다. 규칙기반 응답만 사용됩니다.")

# ------------------------------------------------------------
# 4. 고정 데이터
# ------------------------------------------------------------
PATIENT_INFO: Dict[str, str] = {
    "name": "김심근",
    "registration_number": "2500611",
    "wristband": "김심근 / 등록번호 2500611",
    "age": "62세",
    "sex": "남성",
    "job": "택시기사",
    "route": "응급실 내원",
    "chief_complaint": "가슴이 너무 조이고 답답하며 숨쉬기 힘들다.",
    "pain_location": "가슴 중앙",
    "pain_quality": "누군가 꽉 쥐어짜는 듯한 압박성 통증",
    "radiation": "턱, 왼쪽 어깨, 등",
    "onset": "30분 전 운전 중 갑자기 시작",
    "pain_score_initial": "NRS 8점",
    "associated_symptoms": "호흡곤란, 식은땀, 극심한 불안",
    "aggravating_factors": "가만히 있어도 계속 아프고, 움직이면 더 편해지지 않음",
    "alleviating_factors": "쉬어도 통증이 뚜렷하게 완화되지 않음",
    "history": "고혈압, 6년 전 진단",
    "medication": "혈압약 복용 중이나 약 이름은 모름",
    "anticoagulant_antiplatelet": "최근 항응고제나 항혈소판제는 복용하지 않아요.",
    "bleeding_disorder": "출혈성 질환은 없어요.",
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
    "RR": "32회/분",
    "SpO2": "93%",
    "BT": "36.7℃",
}

LAB_RESULTS: Dict[str, str] = {
    "ECG": "II, III, aVF 유도에서 ST-segment elevation 확인",
    "Troponin I": "12.0 ng/mL",
    "CK-MB": "46 ng/mL",
}

LAB_NORMAL_RANGES: Dict[str, str] = {
    "Troponin I": "< 0.04 ng/mL",
    "CK-MB": "< 3.0–5.0 ng/mL",
}

DOCTOR_ORDER: List[str] = [
    "[처치] O₂ 2 L/min via nasal cannula 적용",
    "[약물] NTG 0.6 mg SL 투여",
    "[약물] Aspirin 300 mg PO 투여",
    "[약물] Plavix 300 mg PO 투여",
    "[약물 PRN] NS 100 mL + morphine 5 mg",
    "[처치] ECG monitoring 유지",
    "[처치] 12-lead ECG re-check",
    "[처치] CAG preparation",
]

POST_INTERVENTION_STATUS: Dict[str, str] = {
    "pain": "NRS 8점에서 3점으로 감소",
    "breathing": "호흡곤란이 다소 완화됨",
    "anxiety": "불안이 감소함",
    "message": "휴… 아까보다는 좀 나아졌어요. 통증이 8점에서 한 3점 정도로 줄어든 것 같고, 숨쉬기도 조금 편해졌어요… 아직 걱정은 되지만 아까보다 덜 불안해요.",
}

POST_INTERVENTION_VITAL_SIGNS: Dict[str, str] = {
    "BP": "138/84 mmHg",
    "HR": "92회/분",
    "RR": "22회/분",
    "SpO2": "96%",
    "BT": "36.7℃",
}

DEBRIEFING_QUESTIONS: List[str] = [
    "환자의 상태를 파악하는 데 가장 중요했던 사정자료는 무엇이었습니까?",
    "검사와 중재의 필요성을 환자에게 어떻게 설명하였으며, 그 설명이 환자의 이해와 참여에 어떤 영향을 주었습니까?",
    "상호작용 단계에서 환자의 주요 문제를 확인하고, 여러 간호문제 중 우선순위를 어떻게 결정하였는지 설명해 보십시오. 이를 바탕으로 환자와 공동 목표 및 목표달성 방법을 어떻게 합의하였습니까?",
    "중재 후 통증, 호흡곤란, 불안 변화와 관련하여 어떤 목표가 달성되었다고 보았습니까?",
]

DEBRIEFING_EXAMPLES: Dict[str, List[str]] = {
    "사정 질문 예시": [
        "가슴 통증이 언제부터 시작되었나요? 위치와 양상은 어떤가요?",
        "통증이 턱, 어깨, 등으로 퍼지나요? 0점부터 10점 중 몇 점 정도인가요?",
        "움직이면 더 심해지거나 가만히 쉬면 나아지나요?",
        "숨이 차거나 식은땀이 나는 증상이 함께 있나요?",
    ],
    "검사 설명 예시": [
        "현재 증상으로 보아 심장 상태를 빨리 확인해야 해서 심전도와 혈액검사가 필요합니다.",
        "심전도는 심장의 전기적 변화를 확인하는 검사이고, 혈액검사는 심장근육 손상 여부를 확인하는 데 도움이 됩니다.",
        "검사 과정이 불안하실 수 있지만 빠르게 상태를 확인하기 위한 과정입니다. 진행해도 괜찮으실까요?",
    ],
    "SBAR 보고 예시": [
        "S: 62세 남성 김심근 환자가 30분 전부터 흉통과 호흡곤란을 호소합니다.",
        "B: 고혈압 과거력, 흡연력, 부친 심장마비 가족력이 있습니다.",
        "A: NRS 8점 흉통, 좌측 어깨·턱·등으로 방사되는 통증, 식은땀, SpO₂ 93%, ECG상 II, III, aVF ST elevation, Troponin I 12.0 ng/mL 상승으로 AMI가 의심됩니다.",
        "R: 산소요법, NTG, Aspirin, Plavix 투여, 12-lead ECG 재확인 및 CAG preparation 처방 확인을 요청드립니다.",
    ],
    "중재 설명 예시": [
        "산소는 숨쉬기 어려운 증상을 완화하고 심장에 산소 공급을 돕기 위해 적용합니다.",
        "니트로글리세린은 혀 밑에서 녹여 흉통 완화에 도움을 주며, 아스피린과 플라빅스는 혈전 생성을 줄이는 데 사용됩니다.",
        "약물 투여 후 어지러움, 두통, 출혈, 통증 악화 등 불편감이 있으면 바로 말씀해주세요. 설명드린 중재를 진행해도 괜찮으실까요?",
    ],
    "재사정 예시": [
        "중재 후 가슴 통증은 0점부터 10점 중 몇 점 정도인가요? NTG 투여 후 혈압과 맥박 등 활력징후를 다시 확인하겠습니다.",
        "숨쉬기는 아까보다 편해지셨나요? 불안감은 조금 줄어들었나요?",
        "처음 함께 설정한 통증 완화, 호흡곤란 감소, 불안 감소 목표가 어느 정도 달성되었다고 생각하시나요?",
        "아직 가장 불편하거나 걱정되는 점이 있나요?",
        "다시 통증이 심해지거나 숨이 차면 바로 말씀해주세요. 계속 관찰하겠습니다.",
    ],
}

# ------------------------------------------------------------
# 5. 체크리스트: 화면 표시 항목과 코드에서 체크하는 항목명 통일
# ------------------------------------------------------------
CHECKLIST_TEMPLATE: Dict[str, bool] = {
    "1. 지각: 초기 접촉 및 주호소 확인": False,
    "2. 지각: 통증 및 동반 증상 사정": False,
    "3. 지각: 활력징후 확인": False,
    "4. 지각: 병력 및 위험요인 사정": False,
    "5. 판단: 심혈관질환 의심 상황 판단 및 검사 필요성 인식": False,
    "6. 행위/반응: 검사 필요성 설명 및 환자의 이해·참여 확인": False,
    "7. 상호작용: 검사결과 기반 문제 구체화": False,
    "8. 상호작용: 간호목표 공유 및 목표달성 방법 확인": False,
    "9. 교류작용: SBAR 보고 및 처방 확인": False,
    "10. 교류작용: 중재 설명 및 중재 수행": False,
    "11. 목표달성: 중재 후 재사정 및 목표달성 확인": False,
    "12. 성찰: 디브리핑": False,
}

# ------------------------------------------------------------
# 6. 세션 상태 초기화
# ------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "started": False,
        "ended": False,
        "messages": [],
        "checklist": CHECKLIST_TEMPLATE.copy(),

        # 표의 프로그램 진행 단계별 상태
        "intro_done": False,
        "pain_symptom_done": False,
        "vitals_done": False,
        "history_risk_done": False,

        # 기본 진행 상태
        "vitals_shown": False,
        "ami_judged": False,
        "labs_shown": False,
        "sbar_reported": False,
        "show_sbar_window": False,
        "order_shown": False,
        "intervention_done": False,
        "reassessment_done": False,
        "goal_achieved": False,
        "cooperation_formed": False,
        "current_phase": "intro",

        # 목표달성 재사정 세부 항목
        # 통증·호흡곤란·불안 3개 증상 확인 후 11단계가 완료됨
        "pain_relief_checked": False,
        "breathing_relief_checked": False,
        "anxiety_relief_checked": False,

        # 검사 설명 누적 인식
        "ecg_explained": False,
        "blood_test_explained": False,
        "exam_cooperation_requested": False,
        "exam_explained": False,
        # 검사 설명 단계에서 핵심 항목이 새로 인식되지 않은 횟수
        # 2회 이상이면 정답이 아닌 누락 항목 중심 힌트를 제공한다.
        "exam_error_count": 0,

        # 상호작용 누적 인식
        "problem_identified": False,
        "goal_set": False,
        "means_explained": False,
        "agreement_obtained": False,
        "interaction_completed": False,
        # 상호작용 단계에서 핵심 항목이 새로 인식되지 않은 횟수
        # 2회 이상이면 정답이 아닌 누락 항목 중심 힌트를 제공한다.
        "interaction_error_count": 0,

        # 상호작용 단계의 목표달성 방법 설명 내부 확인용
        # 화면에는 1개 항목으로만 표시하되, 내부적으로는 4가지가 모두 들어왔는지 확인한다.
        "interaction_oxygen_method_explained": False,
        "interaction_medication_method_explained": False,
        "interaction_ecg_recheck_method_explained": False,
        "interaction_cag_method_explained": False,

        # 중재 설명 누적 인식
        "oxygen_explained": False,
        "medication_explained": False,
        # 약물 설명은 흉통 완화 약물과 혈전 예방 약물 목적을 모두 설명했을 때 완료로 인정한다.
        "medication_pain_relief_explained": False,
        "medication_clot_prevention_explained": False,
        "intervention_purpose_explained": False,
        "side_effect_guidance_given": False,
        "intervention_cooperation_requested": False,
        "intervention_explained": False,
        # 중재 설명 단계에서 핵심 항목이 새로 인식되지 않은 횟수
        # 2회 이상이면 정답이 아닌 누락 항목 중심 힌트를 제공한다.
        "intervention_error_count": 0,

        # 디브리핑
        "show_debriefing": False,
        "debrief_submitted": False,

        # 인식되지 않은 입력에 대한 환자 반응 순차 제시용
        # 0 → 1 → 2 → 다시 0 순서로 환자 반응을 제시한다.
        "unclear_response_index": 0,

        # 환자 대화창에 표시할 현재 단계 라벨
        "_current_response_step_label": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_simulation() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


# ------------------------------------------------------------
# 7. 메시지 및 체크 함수
# ------------------------------------------------------------
def get_current_step_label_for_chat() -> str:
    """환자 대화창에 표시할 현재 진행 단계 라벨을 반환한다."""
    if not st.session_state.get("intro_done", False):
        return "1단계 초기 접촉·주호소 확인"
    if not st.session_state.get("pain_symptom_done", False):
        return "2단계 통증·동반증상 사정"
    if not st.session_state.get("vitals_done", False):
        return "3단계 활력징후 확인"
    if not st.session_state.get("history_risk_done", False):
        return "4단계 병력·위험요인 사정"
    if not st.session_state.get("ami_judged", False):
        return "5단계 심혈관질환 판단·검사 필요성"
    if not st.session_state.get("exam_explained", False):
        return "6단계 검사 설명·참여 확인"
    if not st.session_state.get("labs_shown", False):
        return "7단계 검사결과 확인"
    if not st.session_state.get("interaction_completed", False):
        return "8단계 문제·목표·방법 공유"
    if not st.session_state.get("sbar_reported", False):
        return "9단계 SBAR 보고·처방 확인"
    if not st.session_state.get("intervention_done", False):
        return "10단계 중재 설명·수행"
    if not st.session_state.get("reassessment_done", False):
        return "11단계 재사정·목표달성 확인"
    return "12단계 디브리핑"


def get_step_label_for_category(category: str) -> str:
    """입력 분류 결과를 환자 대화창용 단계 라벨로 변환한다."""
    category_step_map = {
        "intro": "1단계 초기 접촉·주호소 확인",
        "pain_assessment": "2단계 통증·동반증상 사정",
        "vitals": "3단계 활력징후 확인",
        "history_risk": "4단계 병력·위험요인 사정",
        "history": "4단계 병력·위험요인 사정",
        "family_history": "4단계 병력·위험요인 사정",
        "judgment": "5단계 심혈관질환 판단·검사 필요성",
        "ami_judgment": "5단계 심혈관질환 판단·검사 필요성",
        "exam_explanation": "6단계 검사 설명·참여 확인",
        "labs": "7단계 검사결과 확인",
        "interaction_goal_setting": "8단계 문제·목표·방법 공유",
        "report_intro": "9단계 SBAR 보고·처방 확인",
        "report_detail": "9단계 SBAR 보고·처방 확인",
        "intervention_explanation": "10단계 중재 설명",
        "intervention": "10단계 중재 수행",
        "post_intervention_vitals": "11단계 재사정·목표달성 확인",
        "reassessment": "11단계 재사정·목표달성 확인",
        "closing_therapeutic": "11단계 재사정·목표달성 확인",
        "therapeutic": "현재 단계 치료적 의사소통",
        "general": "현재 단계 확인 중",
        "debriefing": "12단계 디브리핑",
    }
    return category_step_map.get(category, get_current_step_label_for_chat())


def patient_message(text: str, stage_label: str = "") -> Dict[str, str]:
    """환자 메시지에 현재 단계 라벨을 함께 저장한다.

    라벨은 render_message()에서 환자 말풍선 안의 작은 배지로 표시된다.
    """
    label = stage_label or st.session_state.get("_current_response_step_label") or get_current_step_label_for_chat()
    return {"role": "assistant", "content": f"[환자] [현재 단계: {label}]\n{text}"}


def system_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[시스템] {text}"}


def patient_verification_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[환자확인] {text}"}


def vital_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[활력징후] {text}"}


def lab_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[검사결과] {text}"}


def order_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[의사 처방] {text}"}


def completion_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[완료 안내] {text}"}


def mark_checklist(item: str) -> None:
    if item in st.session_state.checklist:
        st.session_state.checklist[item] = True


def build_text_progress_bar(progress_ratio: float, bar_length: int = 20) -> str:
    """진행률을 문자형 막대(████░░░░)로 변환한다.

    예: progress_ratio=0.42, bar_length=20이면
    ████████░░░░░░░░░░░░ 형태로 표시된다.
    """
    safe_ratio = min(max(progress_ratio, 0.0), 1.0)
    filled_blocks = round(safe_ratio * bar_length)
    empty_blocks = bar_length - filled_blocks
    return "█" * filled_blocks + "░" * empty_blocks


def render_progress_indicator() -> None:
    """체크리스트 완료 상태를 기반으로 진행률, 문자형 막대, 현재 단계를 사이드바에 표시한다."""
    checklist = st.session_state.get("checklist", CHECKLIST_TEMPLATE.copy())

    total_steps = len(checklist)
    completed_steps = sum(1 for done in checklist.values() if done)
    progress_ratio = completed_steps / total_steps if total_steps > 0 else 0
    progress_percent = progress_ratio * 100
    text_progress_bar = build_text_progress_bar(progress_ratio, bar_length=20)

    current_step = None
    for step, done in checklist.items():
        if not done:
            current_step = step
            break

    st.sidebar.markdown("### 📊 전체 진행률")

    # 숫자 + 문자형 진행 막대
    # 예: Progress: 5 / Step 12 completed
    #     ████████░░░░░░░░░░░░ 42%
    st.sidebar.markdown(
        f"""
        <div style="font-size:1.02rem; line-height:1.55; margin-bottom:8px;">
            <div><strong>Progress: {completed_steps} / Step {total_steps} completed</strong></div>
            <div style="font-family:monospace; font-size:1.05rem; letter-spacing:1px; white-space:nowrap;">
                {text_progress_bar} {progress_percent:.0f}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit 기본 진행률 바도 함께 표시
    st.sidebar.progress(progress_ratio)
    st.sidebar.caption(f"{completed_steps} / {total_steps}단계 완료 ({progress_percent:.0f}%)")

    if current_step:
        st.sidebar.info(f"현재 진행 단계: {current_step}")
    else:
        st.sidebar.success("모든 단계를 완료했습니다.")


def has_any(text: str, keywords: List[str]) -> bool:
    normalized_text = text.lower()
    return any(keyword.lower() in normalized_text for keyword in keywords)


def clean_dialogue_text(text: str) -> str:
    """대화창에 섞인 HTML/CSS/코드 조각을 강제로 제거하고 실제 대화문만 남긴다.

    v14 핵심 수정
    - 이전 버전의 HTML 카드 렌더링에서 저장된 <div style=...> 조각을 모든 메시지 유형에서 제거한다.
    - 정상 태그(<div>...</div>), escape 태그(&lt;div&gt;), 깨진 태그(div style=...>)를 모두 처리한다.
    - Streamlit/PDF 변환 과정에서 섞일 수 있는 특수 문자(, )도 제거한다.
    """
    if text is None:
        return ""

    cleaned = str(text)

    # HTML entity가 여러 번 escape된 경우까지 반복 해제한다.
    for _ in range(50):
        unescaped = unescape(cleaned)
        if unescaped == cleaned:
            break
        cleaned = unescaped

    # PDF/브라우저 캡처에서 섞일 수 있는 특수 제어 문자 제거
    cleaned = cleaned.replace("", "").replace("", "")

    # 코드블록/인라인 코드 표시 제거
    cleaned = re.sub(r"```(?:html|python|text|markdown|css)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").replace("`", "")

    # style/script 블록 전체 제거
    cleaned = re.sub(r"(?is)<\s*style[^>]*>.*?<\s*/\s*style\s*>", "", cleaned)
    cleaned = re.sub(r"(?is)<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", cleaned)

    # br 태그는 줄바꿈으로 변환
    cleaned = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", cleaned)

    # 핵심: 정상 HTML 태그를 모두 제거하되 내부 텍스트는 보존한다.
    # 예: <div style="...">안녕하세요</div> -> 안녕하세요
    cleaned = re.sub(r"(?is)<\s*/?\s*[a-zA-Z][^>]*>", "", cleaned)

    # 깨진 시작 태그 제거: div style="..."> 또는 div style="..." 형태
    cleaned = re.sub(r"(?is)\b(div|span|p|pre|code|section|article)\b\s+[^\n<>]*>", "", cleaned)
    cleaned = re.sub(r"(?is)\b(div|span|p|pre|code|section|article)\b\s+[^\n<>]*(?=\n|$)", "", cleaned)

    # 깨진 닫는 태그 제거: /div>, /span>, </div 조각 등
    cleaned = re.sub(r"(?is)</?\s*(div|span|p|pre|code|section|article)\s*>?", "", cleaned)
    cleaned = re.sub(r"(?is)/\s*(div|span|p|pre|code|section|article)\s*>?", "", cleaned)

    # HTML 속성 조각 제거
    cleaned = re.sub(r"(?is)\b(style|class|id|data-testid|aria-label)\s*=\s*(['\"]).*?\2", "", cleaned)
    cleaned = re.sub(r"(?is)\b(style|class|id|data-testid|aria-label)\s*=\s*[^\s>]+", "", cleaned)

    # CSS 속성 조각 제거
    css_props = [
        "background", "background-color", "border", "border-left", "border-radius",
        "padding", "margin", "line-height", "white-space", "color", "box-shadow",
        "font-size", "font-weight", "width", "display", "gap", "align-items",
        "letter-spacing", "font-family", "height", "min-height", "max-width"
    ]
    cleaned = re.sub(
        r"(?is)(" + "|".join(re.escape(p) for p in css_props) + r")\s*:\s*[^;{}\n]+;?",
        "",
        cleaned,
    )

    # 남은 꺾쇠 조각 제거
    cleaned = re.sub(r"[<>]", "", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")

    # 줄 단위 정리: 태그/속성만 남은 줄 제거
    lines = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[/{},;\s]+", line):
            continue
        if re.fullmatch(r"(?is)(style|class|id|data-testid|aria-label)\s*=.*", line):
            continue
        if re.fullmatch(r"(?is)/?\s*(div|span|p|pre|code|style|script|section|article)\s*", line):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned


def sanitize_message_for_display(msg: Dict[str, str]) -> Dict[str, str]:
    """메시지를 저장/출력하기 전에 HTML/CSS 조각을 제거한다.

    prefix는 유지하되, 본문은 저장 시점과 출력 시점 모두에서 정리한다.
    """
    role = msg.get("role", "assistant")
    content = str(msg.get("content", ""))

    prefixes = [
        "[환자]", "[환자확인]", "[활력징후]", "[검사결과]", "[의사 처방]",
        "[완료 안내]", "[시스템]", "[학습 힌트]", "[학습 안내]"
    ]
    for prefix in prefixes:
        if content.startswith(prefix):
            body = content.replace(prefix, "", 1).strip()
            return {"role": role, "content": (prefix + " " + clean_dialogue_text(body)).strip()}

    return {"role": role, "content": clean_dialogue_text(content)}


def safe_message(msg: Dict[str, str]) -> Dict[str, str]:
    """메시지를 저장하기 직전에 HTML/CSS 조각을 제거한다."""
    return sanitize_message_for_display(msg)




def is_ami_judgment_statement(text: str) -> bool:
    """심근경색 또는 심장·심혈관 문제 가능성 판단 문장을 유연하게 인식한다.

    수정 목적
    - '급성심근경색/AMI/STEMI'처럼 정확한 진단명뿐 아니라
      '심장질환', '심장 문제', '심혈관 문제', 'heart disease',
      'heart problem', 'cardiovascular problem', 'possible heart problem' 같은 표현도
      5단계 판단·검사 필요성 인식으로 인정한다.
    - 단, 너무 모호한 표현만으로 넘어가지 않도록 의심/가능성 표현 또는
      심전도·혈액검사 필요성 표현이 함께 있을 때 인정한다.
    """
    raw = str(text or "").lower()
    compact = re.sub(r"\s+", "", raw)

    disease_terms = [
        # 기존 AMI 관련 표현
        "급성심근경색", "급성 심근경색", "심근경색", "심근 경색",
        "심장마비", "심장 마비", "ami", "stemi",
        "acute myocardial infarction", "myocardial infarction", "heart attack",

        # 추가: 넓은 심장/심혈관 문제 표현
        "심장질환", "심장 질환", "심질환",
        "심장문제", "심장 문제", "심장쪽 문제", "심장 쪽 문제",
        "심장에 문제", "심장에 문제가", "심장 이상", "심장 관련 문제", "심장 관련 질환",
        "심혈관문제", "심혈관 문제", "심혈관질환", "심혈관 질환", "심혈관계 문제",
        "심혈관계질환", "심혈관계 질환",

        "heart disease", "heart problem", "heart problems", "heart issue", "heart issues",
        "possible heart problem", "possible heart disease",
        "cardiac problem", "cardiac problems", "cardiac issue", "cardiac issues", "cardiac disease",
        "cardiovascular problem", "cardiovascular problems", "cardiovascular issue",
        "cardiovascular issues", "cardiovascular disease",
    ]
    disease_terms_compact = [re.sub(r"\s+", "", term.lower()) for term in disease_terms]

    suspicion_terms = [
        "의심", "가능성", "가능", "보입니다", "보여", "보여요",
        "같습니다", "같아요", "생각", "추정", "우려",
        "suspect", "suspected", "suspicious", "possible", "likely",
        "is suspected", "seems", "appears", "concern", "concerned",
        "may be", "might be", "could be",
    ]
    suspicion_terms_compact = [re.sub(r"\s+", "", term.lower()) for term in suspicion_terms]

    test_terms = [
        "심전도", "ecg", "ekg",
        "혈액검사", "혈액 검사", "피검사", "피 검사",
        "심근효소", "심근 효소", "트로포닌", "troponin",
        "ck-mb", "ckmb", "cardiac enzyme", "blood test", "blood work",
    ]
    test_terms_compact = [re.sub(r"\s+", "", term.lower()) for term in test_terms]

    need_terms = [
        "필요", "해야", "확인해야", "검사해야", "시행", "진행",
        "확인", "검사", "파악",
        "need", "needed", "necessary", "should", "must", "required",
        "confirm", "check", "verify",
    ]
    need_terms_compact = [re.sub(r"\s+", "", term.lower()) for term in need_terms]

    current_symptom_terms = [
        "현재증상", "현재 증상", "증상으로", "자료를종합", "자료를 종합",
        "흉통", "가슴통증", "가슴 통증", "가슴답답", "가슴 답답",
        "호흡곤란", "호흡 곤란", "식은땀", "방사통",
        "current symptoms", "symptoms", "chest pain", "chest discomfort",
        "shortness of breath", "dyspnea",
    ]
    current_terms_compact = [re.sub(r"\s+", "", term.lower()) for term in current_symptom_terms]

    has_disease = any(term in compact for term in disease_terms_compact)
    has_suspicion = any(term in compact for term in suspicion_terms_compact)
    has_test = any(term in compact for term in test_terms_compact)
    has_need = any(term in compact for term in need_terms_compact)
    has_current_context = any(term in compact for term in current_terms_compact)

    # 예: "현재 증상으로 급성심근경색이 의심됩니다."
    # 예: "심장 문제일 가능성이 있습니다."
    # 예: "It could be a heart problem."
    if has_disease and has_suspicion:
        return True

    # 예: "심장 문제인지 확인하기 위해 심전도와 혈액검사가 필요합니다."
    # 예: "We need ECG and blood tests to check for a possible heart problem."
    if has_disease and has_test and has_need:
        return True

    # 예: "현재 흉통과 호흡곤란이 있어 심전도와 혈액검사가 필요합니다."
    if has_current_context and has_test and has_need:
        return True

    return False

def is_labs_transition_expression(text: str) -> bool:
    """검사 설명 완료 후 검사결과 확인 단계로 넘어가는 표현을 폭넓게 인식한다.

    핵심 보완점
    - has_any()는 단순 부분 문자열 비교라서 "test execution"과 "execution of test"를
      같은 뜻으로 이해하지 못한다.
    - 따라서 검사 시행/진행/결과 확인을 의미하는 한국어·영어 표현을 별도로 모아 확인한다.
    - 이 함수는 주로 Step 6 완료 후 Step 7 검사결과 확인으로 넘어갈 때 사용한다.
    """
    raw = str(text or "").lower().strip()
    compact = re.sub(r"[\s\-_/.,:;!?()\[\]{}]+", "", raw)

    phrases = [
        # Korean: 검사 시행/진행/수행
        "검사 진행", "검사를 진행", "검사 진행하겠습니다", "검사를 진행하겠습니다",
        "검사 진행할게요", "검사를 진행할게요", "검사 시행", "검사를 시행",
        "검사 시행하겠습니다", "검사를 시행하겠습니다", "검사 실시", "검사를 실시",
        "검사 실시하겠습니다", "검사를 실시하겠습니다", "검사 수행", "검사를 수행",
        "검사 수행하겠습니다", "검사를 수행하겠습니다", "검사하겠습니다", "검사 하겠습니다",
        "검사 해보겠습니다", "검사를 해보겠습니다", "검사 해드리겠습니다", "검사해드리겠습니다",
        "검사 시작", "검사를 시작", "검사 시작하겠습니다", "검사를 시작하겠습니다",
        "바로 검사", "지금 검사", "검사 들어가겠습니다",

        # Korean: 검사결과 확인
        "검사 결과 확인", "검사결과 확인", "검사 결과를 확인", "검사결과를 확인",
        "검사 결과 확인하겠습니다", "검사 결과를 확인하겠습니다",
        "검사결과 확인하겠습니다", "검사결과를 확인하겠습니다",
        "검사 수치 확인", "검사수치 확인", "결과 확인", "결과를 확인",
        "결과 확인하겠습니다", "결과를 확인하겠습니다",

        # English: conduct/perform/run/proceed/check results
        "conduct the test", "conduct a test", "conduct tests", "conduct an inspection", "conduct inspection",
        "we will conduct the test", "we will conduct a test", "we will conduct tests",
        "we will conduct an inspection", "i will conduct the test", "i will conduct an inspection",
        "perform the test", "perform a test", "perform tests", "we will perform the test",
        "run the test", "run tests", "we will run the test", "do the test", "do tests",
        "proceed with the test", "proceed with testing", "proceed with the inspection",
        "proceed with an inspection", "proceed with inspection", "we will proceed with the test",
        "we will proceed with the inspection",
        "carry out the test", "carry out tests", "carry out the inspection",
        "implement the test", "implement testing", "test implementation",
        "test execution", "execution of test", "execution of the test",
        "test progress", "progress of test", "progress of the test", "inspection progress",
        "check the results", "check results", "check the test results", "check test results",
        "i will check the results", "i will check the test results",
        "we will check the results", "we will check the test results",
    ]
    compact_phrases = [re.sub(r"[\s\-_/.,:;!?()\[\]{}]+", "", phrase.lower()) for phrase in phrases]
    return any(phrase in raw for phrase in phrases) or any(phrase in compact for phrase in compact_phrases)


def is_valid_interaction_goal_statement(text: str) -> bool:
    """상호작용 단계의 '간호목표 공유'가 실제 임상 목표인지 확인한다.

    v30 수정
    - 기존에는 '목표'라는 단어만 포함되어도 goal_set=True가 되어
      '목표는 바나나입니다'처럼 부적절한 답변도 다음 단계로 넘어가는 문제가 있었다.
    - 따라서 목표라는 단어 자체가 아니라, AMI 상황에서 적절한 목표 내용
      즉 통증 완화, 호흡곤란 감소, 불안 감소/안정이 포함될 때만 인정한다.
    """
    raw = str(text or "").lower()
    compact = re.sub(r"\s+", "", raw)

    # 명백히 부적절한 예시/무관 단어는 목표로 인정하지 않는다.
    invalid_terms = [
        "바나나", "banana", "bananas", "사과", "apple", "apples",
        "딸기", "strawberry", "커피", "coffee", "아무거나", "모르겠", "몰라"
    ]
    invalid_compact = [re.sub(r"\s+", "", term.lower()) for term in invalid_terms]
    if any(term in compact for term in invalid_compact):
        return False

    pain_terms = [
        "통증", "흉통", "가슴통증", "가슴 통증", "가슴답답", "가슴 답답",
        "pain", "chest pain", "chest discomfort"
    ]
    breathing_terms = [
        "호흡곤란", "호흡 곤란", "숨쉬기", "숨 쉬기", "숨찬", "숨 차", "호흡",
        "breathing", "shortness of breath", "dyspnea", "dyspnoea", "breath"
    ]
    anxiety_terms = [
        # "안정/안심"은 개선 표현으로만 사용한다.
        # 이를 증상어로도 넣으면 "목표는 안정입니다" 같은 모호한 답변이 통과될 수 있다.
        "불안", "불안감", "걱정", "두려움", "무서움",
        "anxiety", "anxious", "worry", "fear"
    ]
    improvement_terms = [
        "줄", "감소", "완화", "경감", "낮추", "조절", "완전히 없", "편하게", "편해",
        "호전", "개선", "안정", "안심", "덜", "relieve", "relief", "reduce", "decrease",
        "lessen", "ease", "control", "improve", "stabilize", "stable", "comfortable"
    ]
    goal_context_terms = [
        "목표", "공동목표", "공동 목표", "치료목표", "치료 목표", "간호목표", "간호 목표",
        "goal", "goals", "aim", "objective", "target", "plan is to", "we want to", "we aim to"
    ]

    def contains_any(terms):
        compact_terms = [re.sub(r"\s+", "", term.lower()) for term in terms]
        return any(term in raw for term in terms) or any(term in compact for term in compact_terms)

    has_goal_context = contains_any(goal_context_terms)
    has_improvement = contains_any(improvement_terms)
    has_pain = contains_any(pain_terms)
    has_breathing = contains_any(breathing_terms)
    has_anxiety = contains_any(anxiety_terms)

    # '목표는 통증 완화/호흡곤란 감소/불안 감소'처럼 목표 맥락과 임상 목표가 함께 있으면 인정한다.
    if has_goal_context and has_improvement and (has_pain or has_breathing or has_anxiety):
        return True

    # 학생이 질문에 대한 답으로 '통증을 줄이고 숨쉬기 편하게 하겠습니다'처럼
    # 목표라는 단어 없이도 적절한 임상 목표를 제시하면 인정한다.
    symptom_goal_count = sum([
        has_pain and has_improvement,
        has_breathing and has_improvement,
        has_anxiety and has_improvement,
    ])
    if symptom_goal_count >= 1 and (has_pain or has_breathing or has_anxiety):
        return True

    return False


def is_exam_cooperation_response(text: str) -> bool:
    """검사 설명이 이미 완료된 맥락에서 짧은 진행 표현을 검사 참여 확인으로 인식한다.

    주의: 이 함수는 단독으로 검사 설명 단계를 완료시키기 위한 것이 아니다.
    반드시 심전도 설명과 혈액검사 설명이 모두 완료된 상태에서만 사용한다.
    예: “네”, “바로 가능합니다”, “검사 진행하겠습니다”, “검사 결과 확인하겠습니다”.
    """
    exam_cooperation_keywords = [
        # 짧은 수락/진행 표현
        "네", "예", "넵", "네네", "알겠습니다", "좋습니다", "괜찮습니다",
        "가능합니다", "바로 가능합니다", "지금 가능합니다", "바로 가능", "지금 가능",

        # 검사 진행 표현
        "검사 진행", "검사를 진행", "검사하겠습니다", "검사 하겠습니다",
        "검사 해드리겠습니다", "검사해드리겠습니다", "검사 도와드릴게요",
        "진행하겠습니다", "진행 하겠습니다", "진행할게요", "진행 할게요",
        "바로 진행", "지금 진행", "바로 시행", "지금 시행",
        "시작하겠습니다", "시작 하겠습니다", "시작할게요",
        "바로 해드리겠습니다", "바로 해드릴게요", "해드리겠습니다", "도와드릴게요",

        # 검사 이후 결과 확인으로 넘어가려는 표현
        "검사실 확인", "검사 결과 확인", "검사결과 확인",
        "검사 결과를 확인", "검사결과를 확인", "검사 결과 확인하겠습니다", "검사 결과를 확인하겠습니다",
        "검사결과 확인하겠습니다", "검사결과를 확인하겠습니다", "검사 결과 보겠습니다", "검사결과 보겠습니다",
        "결과 확인", "결과를 확인", "검사 후 결과", "결과를 확인하겠습니다",

        # 기존 협조/동의 표현
        "협조", "협조해 주실 수", "협조해주시겠", "동의", "동의하시",
        "괜찮을까요", "괜찮으실까요", "진행해도", "진행해도 될까요",
        "검사해도 될까요", "검사를 해도 될까요", "해도 될까요",

        # 영어 표현
        "agree", "consent", "proceed", "can we proceed", "may i proceed",
        "is it okay", "okay to proceed", "we can proceed", "start the test",
        "conduct the test", "conduct a test", "conduct an inspection", "conduct inspection",
        "we will conduct the test", "we will conduct an inspection",
        "proceed with the test", "proceed with an inspection", "proceed with inspection",
        "perform the test", "run the test", "check the results", "check the test results",
        "i will check the results", "i will check the test results", "we will check the test results"
    ]
    return has_any(text, exam_cooperation_keywords) or is_labs_transition_expression(text)



def is_intervention_cooperation_response(text: str) -> bool:
    """중재 설명이 충분히 이루어진 맥락에서 짧은 동의/진행 표현을 중재 참여 확인으로 인식한다.

    주의: 이 함수는 단독으로 중재 설명 단계를 완료시키기 위한 것이 아니다.
    산소요법, 약물투여, 중재 목적, 이상반응/불편감 안내가 모두 충족된 상태에서만
    중재 참여 확인으로 인정한다.
    """
    intervention_cooperation_keywords = [
        "동의", "동의하시", "동의하시나요", "동의해주세요", "동의해 주세요", "동의해주시면",
        "괜찮을까요", "괜찮으실까요", "괜찮으시면", "괜찮다면",
        "진행해도", "진행해도 될까요", "진행해도 괜찮", "진행하겠습니다", "바로 진행",
        "시작하겠습니다", "시작할게요", "해도 될까요", "설명 들으셨으면", "설명 이해되셨으면",
        "협조", "협조해 주실 수", "협조해주시겠", "협조 부탁",
        "agree", "consent", "proceed", "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]
    return has_any(text, intervention_cooperation_keywords)


def is_reassessment_input(text: str) -> bool:
    """중재 수행 후 재사정 단계에서 통증·호흡곤란·불안·목표달성 관련 입력인지 확인한다."""
    reassessment_keywords = [
        "재사정", "다시 확인", "상태를 다시", "치료 후", "중재 후", "처치 후", "약물 투여 후", "산소 적용 후",
        "통증", "흉통", "가슴 통증", "가슴통증", "몇 점", "nrs", "통증척도", "통증 점수",
        "아프", "괜찮", "나아", "나아졌", "줄어", "감소", "완화", "호전", "처음보다", "아까보다",
        "숨", "호흡", "호흡곤란", "호흡 곤란", "숨쉬기", "숨 쉬기", "숨찬", "산소포화도", "spo2",
        "불안", "불안감", "걱정", "무섭", "두려움", "안정",
        "목표", "목표 달성", "목표가 달성", "달성", "3가지", "세 가지", "모두 확인",
        "가장 불편", "가장 걱정", "아직 불편", "아직 걱정",
        "reassess", "re-assess", "after treatment", "after intervention", "pain", "pain score",
        "breathing", "dyspnea", "shortness of breath", "anxiety", "anxious", "goal achieved"
    ]
    return has_any(text, reassessment_keywords)

def count_true(values: List[bool]) -> int:
    return sum(1 for value in values if value)


def get_unclear_patient_response() -> str:
    """학습자 입력이 현재 단계의 인식 기준에 맞지 않을 때 환자 반응을 순서대로 제시한다.

    예: 1번째 미인식 입력 → 1번 반응, 2번째 → 2번 반응,
    3번째 → 3번 반응, 4번째 → 다시 1번 반응.
    임상정보나 진행 조건은 바꾸지 않고, 환자의 불안·혼란 표현만 다양화한다.
    """
    unclear_responses = [
        "네… 제가 잘 이해하지 못했어요. 다시 한 번 쉽게 설명해 주실 수 있을까요?",
        "죄송한데… 지금 너무 불안해서 잘 못 알아들었어요. 조금 더 쉽게 설명해 주세요.",
        "선생님, 무슨 뜻인지 아직 잘 모르겠어요… 제가 지금 무엇을 해야 하는지 다시 말씀해 주실 수 있을까요?",
    ]

    # 기존 세션이나 수정 전 파일을 실행한 경우에도 오류가 나지 않도록 기본값을 보정한다.
    if "unclear_response_index" not in st.session_state:
        st.session_state.unclear_response_index = 0

    index = st.session_state.unclear_response_index
    selected_response = unclear_responses[index % len(unclear_responses)]

    # 다음 미인식 입력에서는 다음 문장이 나오도록 1 증가시킨다.
    st.session_state.unclear_response_index = index + 1

    return selected_response

def update_reassessment_state(text: str) -> List[str]:
    """중재 후 통증, 호흡곤란, 불안 완화 여부를 각각 누적 인식한다.

    중재 후에는 같은 '통증/숨/불안' 표현도 초기 사정이 아니라 재사정으로 처리한다.
    '통증 완화, 호흡곤란 감소, 불안 감소 목표가 모두 달성되었나요?'처럼
    세 가지 목표를 한 번에 확인하는 문장도 모두 체크한다.
    """
    updates: List[str] = []

    pain_keywords = [
        "통증", "흉통", "가슴 통증", "가슴통증", "nrs", "통증척도", "통증 점수",
        "몇 점", "아픈", "아프", "pain", "pain score"
    ]
    breathing_keywords = [
        "호흡곤란", "호흡 곤란", "숨쉬기", "숨 쉬기", "숨", "숨찬", "숨 차",
        "호흡", "산소포화도", "spo2", "breathing", "shortness of breath", "dyspnea"
    ]
    anxiety_keywords = [
        "불안", "불안감", "걱정", "두려움", "무서", "안정", "anxiety", "anxious", "worry"
    ]
    all_goal_keywords = [
        "목표 달성", "목표가 달성", "목표는 달성", "목표 달성 여부", "목표달성",
        "통증 완화", "호흡곤란 감소", "불안 감소", "3가지", "세 가지", "모두 확인", "모두 달성"
    ]

    # 세 가지 목표를 한 번에 확인하는 문장은 통증·호흡곤란·불안 확인을 모두 완료로 인정한다.
    if (
        has_any(text, all_goal_keywords)
        and has_any(text, pain_keywords)
        and has_any(text, breathing_keywords)
        and has_any(text, anxiety_keywords)
    ):
        if not st.session_state.pain_relief_checked:
            st.session_state.pain_relief_checked = True
            updates.append("통증 완화 확인")
        if not st.session_state.breathing_relief_checked:
            st.session_state.breathing_relief_checked = True
            updates.append("호흡곤란 감소 확인")
        if not st.session_state.anxiety_relief_checked:
            st.session_state.anxiety_relief_checked = True
            updates.append("불안 감소 확인")
        return updates

    if has_any(text, pain_keywords):
        if not st.session_state.pain_relief_checked:
            updates.append("통증 완화 확인")
        st.session_state.pain_relief_checked = True
    if has_any(text, breathing_keywords):
        if not st.session_state.breathing_relief_checked:
            updates.append("호흡곤란 감소 확인")
        st.session_state.breathing_relief_checked = True
    if has_any(text, anxiety_keywords):
        if not st.session_state.anxiety_relief_checked:
            updates.append("불안 감소 확인")
        st.session_state.anxiety_relief_checked = True

    return updates


def get_reassessment_patient_response_for_current_state(updates: List[str]) -> str:
    """재사정 단계에서 중재 후 고정 반응만 반환한다.

    중재 후 단계에서는 OpenAI 자연화나 초기 환자 반응을 사용하지 않는다.
    따라서 통증·호흡곤란·불안 질문이 초기 사정으로 되돌아가는 상태 전환 오류를 방지한다.
    """
    response_parts = []

    if "통증 완화 확인" in updates:
        response_parts.append("가슴 통증은 처음 8점에서 지금은 3점 정도로 줄었어요.")

    if "호흡곤란 감소 확인" in updates:
        response_parts.append("숨쉬기는 아까보다 조금 편해졌어요.")

    if "불안 감소 확인" in updates:
        response_parts.append("불안도 아까보다는 많이 줄었어요. 아직 조금 걱정은 되지만 처음보다는 안정됐어요.")

    if response_parts:
        return " ".join(response_parts)

    # 학생이 “중재 후 상태를 다시 확인하겠습니다”처럼 포괄적으로 말한 경우에는
    # 통증 3점/호흡 완화/불안 감소 값을 먼저 노출하지 않는다.
    # 재사정 단계의 학습 목표는 학생이 통증·호흡곤란·불안을 각각 확인하는 것이므로,
    # 구체적인 항목을 질문하도록 유도한다.
    return (
        "네… 중재 후 상태를 다시 확인해 주세요. "
        "가슴 통증, 숨쉬기, 불안감 중 어떤 부분을 먼저 확인해 주실 건가요?"
    )

def reassessment_symptoms_all_checked() -> bool:
    """통증, 호흡곤란, 불안 완화 확인이 모두 끝났는지 확인한다."""
    return (
        st.session_state.pain_relief_checked
        and st.session_state.breathing_relief_checked
        and st.session_state.anxiety_relief_checked
    )


def reassessment_all_checked() -> bool:
    """통증·호흡곤란·불안 완화 확인이 모두 끝났는지 확인한다."""
    return reassessment_symptoms_all_checked()


def is_post_intervention_vitals_request(text: str) -> bool:
    """중재 후 활력징후 재측정 요청인지 확인한다."""
    vitals_keywords = [
        "활력징후", "활력 징후", "혈압", "맥박", "호흡수", "산소포화도", "spo2", "체온",
        "vital signs", "blood pressure", "pulse", "heart rate", "respiratory rate",
        "oxygen saturation", "temperature", "bt"
    ]
    recheck_keywords = [
        "다시", "재측정", "재 측정", "측정", "확인", "사정", "재사정",
        "remeasure", "re-measure", "check", "recheck", "re-check", "assess", "reassess", "re-assess"
    ]
    return has_any(text, vitals_keywords) and has_any(text, recheck_keywords)


def post_intervention_vital_response() -> Dict[str, str]:
    """중재 직후 환자 반응 다음에 표시할 중재 후 활력징후와 5분 후 재사정 안내를 하나의 시스템 메시지로 반환한다."""
    return vital_message(
        "중재 후 활력징후 재측정\n"
        f"- BP: {POST_INTERVENTION_VITAL_SIGNS['BP']}\n"
        f"- HR: {POST_INTERVENTION_VITAL_SIGNS['HR']}\n"
        f"- RR: {POST_INTERVENTION_VITAL_SIGNS['RR']}\n"
        f"- SpO₂: {POST_INTERVENTION_VITAL_SIGNS['SpO2']}\n"
        f"- BT: {POST_INTERVENTION_VITAL_SIGNS['BT']}\n\n"
        "5분 후 환자의 통증 완화 여부, 호흡곤란 감소 여부, 불안 감소 여부를 확인하세요."
    )


def get_exam_patient_response_for_current_state(updates: List[str]) -> str:
    """검사 설명 단계에서 현재 누적 상태에 맞는 환자 반응을 반환한다."""
    if st.session_state.ecg_explained and not st.session_state.blood_test_explained:
        return "심전도로 심장 상태를 확인한다는 건 이해했어요… 그런데 피검사는 왜 필요한지도 설명해 주실 수 있을까요?"
    if st.session_state.blood_test_explained and not st.session_state.ecg_explained:
        return "피검사로 심장근육 손상 여부를 본다는 건 알겠어요… 심전도 검사는 왜 필요한지도 쉽게 설명해 주세요."
    if (
        st.session_state.ecg_explained
        and st.session_state.blood_test_explained
        and not st.session_state.exam_cooperation_requested
    ):
        return "심전도랑 피검사가 왜 필요한지는 이제 조금 이해했어요… 지금 바로 검사 진행해도 되는 건가요?"
    if updates:
        return "조금 이해됐어요… 그래도 심전도와 혈액검사가 각각 왜 필요한지 빠진 부분을 한 번만 더 쉽게 설명해 주세요."
    return "선생님… 심전도와 피검사를 한다는 건 알겠는데, 각각 왜 필요한 검사인지 아직 잘 모르겠어요. 쉽게 설명해 주시면 협조할게요…"


def get_interaction_patient_response_for_current_state(updates: List[str]) -> str:
    """상호작용 단계에서 현재 순서에 맞는 환자 반응을 반환한다.

    진행 순서:
    1) 환자 문제 확인
    2) 간호목표 공유
    3) 목표달성 방법 설명
    4) 환자의 이해와 참여 확인
    
    중요: 환자는 아직 설명받지 않은 목표달성 방법을 먼저 말하지 않는다.
    """
    if not st.session_state.problem_identified:
        return "선생님… 검사 결과가 안 좋다고 하니 너무 불안해요. 지금 제 상태에서 무엇이 가장 문제인지 쉽게 설명해 주세요…"

    if st.session_state.problem_identified and not st.session_state.goal_set:
        return "네… 제일 힘든 건 가슴 통증이랑 숨찬 거예요. 그럼 지금 치료 목표는 무엇인지 설명해 주세요."

    if st.session_state.problem_identified and st.session_state.goal_set and not st.session_state.means_explained:
        return "제 문제와 목표는 이해했어요… 그 목표를 위해 앞으로 어떤 치료나 간호를 받게 되는지 알려주세요."

    if st.session_state.problem_identified and st.session_state.goal_set and st.session_state.means_explained and not st.session_state.agreement_obtained:
        return "산소요법, 약물치료, 심전도 재확인, 관상동맥조영술 준비 가능성까지 설명해 주셔서 이해했어요… 제가 협조하면 되는 건가요?"

    return "네… 설명해 주신 내용은 이해했어요. 말씀하신 방법에 협조하겠습니다."




def get_exam_missing_items() -> List[str]:
    """검사 설명 단계에서 아직 충족되지 않은 항목을 반환한다."""
    missing = []
    if not st.session_state.ecg_explained:
        missing.append("심전도는 심장의 전기적 변화나 리듬을 확인하는 검사라는 설명")
    if not st.session_state.blood_test_explained:
        missing.append("혈액검사는 심장근육 손상 여부 또는 Troponin/CK-MB 같은 심장 손상 지표를 확인하는 검사라는 설명")
    if st.session_state.ecg_explained and st.session_state.blood_test_explained and not st.session_state.exam_cooperation_requested:
        missing.append("검사를 진행해도 되는지 환자의 이해와 참여 의사 확인")
    return missing


def get_exam_hint_text() -> str:
    """검사 설명 단계에서 2회 이상 막혔을 때 제공할 표준화된 힌트."""
    missing = get_exam_missing_items()
    if missing:
        missing_text = "\n".join([f"- {item}" for item in missing])
    else:
        missing_text = "- 심전도 설명, 혈액검사 설명, 검사 참여 확인을 모두 포함해 보세요."
    return (
        "검사 설명 단계에서 아직 빠진 핵심 항목이 있습니다. 정답 문장을 그대로 제시하지는 않으니, "
        "아래 항목을 참고해 자신의 말로 다시 설명해보세요.\n"
        f"{missing_text}\n"
        "예: 심전도는 심장의 전기적 변화/리듬 확인, 혈액검사는 심장근육 손상 여부 확인과 연결해서 설명한 뒤 "
        "검사를 진행해도 되는지 확인합니다. 이미 두 검사의 목적을 설명했다면 ‘네, 바로 검사 진행하겠습니다’처럼 "
        "짧게 진행 의사를 확인해도 됩니다."
    )


def get_interaction_missing_items() -> List[str]:
    """상호작용 단계에서 아직 충족되지 않은 항목을 반환한다."""
    missing = []
    if not st.session_state.problem_identified:
        missing.append("검사결과를 바탕으로 현재 주요 문제 확인")
    if not st.session_state.goal_set:
        missing.append("통증 완화, 호흡곤란 감소, 불안 감소를 공동 목표로 공유")

    method_missing = []
    if not st.session_state.interaction_oxygen_method_explained:
        method_missing.append("산소요법")
    if not st.session_state.interaction_medication_method_explained:
        method_missing.append("약물치료")
    if not st.session_state.interaction_ecg_recheck_method_explained:
        method_missing.append("심전도 재확인")
    if not st.session_state.interaction_cag_method_explained:
        method_missing.append("관상동맥조영술 준비 가능성")
    if method_missing:
        missing.append("목표달성 방법 설명: " + ", ".join(method_missing))

    if not st.session_state.agreement_obtained:
        missing.append("환자가 설명을 이해하고 협조할 수 있는지 확인")
    return missing


def get_interaction_hint_text() -> str:
    """상호작용 단계에서 2회 이상 막혔을 때 제공할 표준화된 힌트."""
    missing = get_interaction_missing_items()
    if missing:
        missing_text = "\n".join([f"- {item}" for item in missing])
    else:
        missing_text = "- 문제 확인, 목표 공유, 목표달성 방법 설명, 이해와 참여 확인을 모두 포함해 보세요."
    return (
        "상호작용 단계에서 아직 빠진 핵심 항목이 있습니다. 정답 문장을 그대로 제시하지는 않으니, "
        "아래 항목을 참고해 자신의 말로 다시 설명해보세요.\n"
        f"{missing_text}\n"
        "예: 현재 문제를 확인하고 통증·호흡곤란·불안 완화를 목표로 공유한 뒤, 산소요법, 약물치료, "
        "심전도 재확인, 관상동맥조영술 준비 가능성을 설명하고 협조 여부를 확인합니다."
    )


def get_intervention_missing_items() -> List[str]:
    """중재 설명 단계에서 아직 충족되지 않은 항목을 반환한다."""
    missing = []
    if not st.session_state.oxygen_explained:
        missing.append("산소요법이 호흡곤란 완화와 심장 산소 공급에 도움이 된다는 설명")

    if not st.session_state.medication_explained:
        medication_missing = []
        if not st.session_state.get("medication_pain_relief_explained", False):
            medication_missing.append("NTG/니트로글리세린 등 흉통 완화 약물의 목적")
        if not st.session_state.get("medication_clot_prevention_explained", False):
            medication_missing.append("아스피린과 플라빅스 등 혈전 예방 약물의 목적")
        if medication_missing:
            missing.append("약물의 구체적 목적: " + ", ".join(medication_missing))
        else:
            missing.append("약물이 흉통 완화와 혈전 예방에 도움이 된다는 설명")

    if not st.session_state.intervention_purpose_explained:
        missing.append("중재가 통증 완화, 호흡곤란 감소, 심장 부담 감소에 어떤 도움이 되는지 설명")

    if not st.session_state.side_effect_guidance_given:
        missing.append("어지러움, 두통, 출혈, 통증 악화, 불편감 발생 시 바로 말씀하거나 콜벨로 간호사를 부르도록 안내")

    # 동의/협조 확인은 설명이 충분히 이루어진 뒤 다시 확인해야 하므로, 아직 인정되지 않았으면 누락 항목으로 보여준다.
    if not st.session_state.intervention_cooperation_requested:
        missing.append("설명한 중재에 대한 환자의 이해와 참여 의사 또는 동의 확인")

    return missing

def get_intervention_hint_text() -> str:
    """중재 설명 단계에서 2회 이상 막혔을 때 제공할 표준화된 힌트."""
    missing = get_intervention_missing_items()
    if missing:
        missing_text = "\n".join([f"- {item}" for item in missing])
    else:
        missing_text = "- 산소요법 설명, 약물투여 설명, 중재 목적, 이상반응/불편감 안내, 동의/협조 확인을 모두 포함해 보세요."
    return (
        "중재 설명 단계에서 아직 빠진 핵심 항목이 있습니다. 정답 문장을 그대로 제시하지는 않으니, "
        "아래 항목을 참고해 자신의 말로 다시 설명해보세요.\n"
        f"{missing_text}\n"
        "예: 산소는 숨쉬기와 심장 산소 공급을 돕고, NTG는 흉통 완화, 아스피린과 플라빅스는 혈전 예방에 도움이 됩니다. "
        "어지러움·두통·출혈·통증 악화·불편감이 있으면 바로 말씀하거나 콜벨을 누르도록 안내한 뒤, "
        "설명한 중재를 진행해도 되는지 확인합니다."
    )

def get_intervention_patient_response_for_current_state(updates: List[str]) -> str:
    """중재 설명 단계에서 현재 누락된 항목에 맞춰 환자 반응을 반환한다."""
    pain_med_done = st.session_state.get("medication_pain_relief_explained", False)
    clot_med_done = st.session_state.get("medication_clot_prevention_explained", False)

    if not st.session_state.oxygen_explained:
        return "선생님… 산소는 왜 필요한 건가요? 숨쉬는 데 어떤 도움이 되는지 쉽게 설명해 주세요."

    if st.session_state.oxygen_explained and not st.session_state.medication_explained:
        if pain_med_done and not clot_med_done:
            return "통증 완화에 도움이 되는 약은 이해했어요… 그런데 아스피린이나 플라빅스 같은 약은 왜 필요한지도 설명해 주세요."
        if clot_med_done and not pain_med_done:
            return "혈전 예방 약은 이해했어요… 그런데 가슴 통증 완화를 위해 쓰는 약은 왜 필요한지도 설명해 주세요."
        return "산소가 숨쉬는 데 도움이 된다는 건 알겠어요… 그런데 약은 어떤 약이고 왜 필요한가요?"

    if st.session_state.medication_explained and not st.session_state.oxygen_explained:
        return "약이 가슴 통증과 혈전 예방에 도움이 된다는 건 알겠어요… 산소는 왜 필요한지도 쉽게 설명해 주세요."

    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and not st.session_state.intervention_purpose_explained
    ):
        return "산소와 약을 한다는 건 알겠어요… 이게 제 가슴 통증이나 숨찬 증상에 어떤 도움이 되는지 설명해 주세요."

    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and not st.session_state.side_effect_guidance_given
    ):
        return "왜 필요한지는 이해했어요… 그런데 약이나 산소를 하다가 어지럽거나 불편하면 어떻게 해야 하나요?"

    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and st.session_state.side_effect_guidance_given
        and not st.session_state.intervention_cooperation_requested
    ):
        return "불편하면 말씀드리거나 콜벨을 누르면 되는 것도 알겠어요… 그럼 지금 제가 동의하면 바로 진행하는 건가요?"

    if updates:
        return "조금 이해됐어요… 제가 빠뜨린 부분 없이 안심하고 협조할 수 있도록 한 번만 더 쉽게 설명해 주세요."

    return "선생님… 지금 무엇을 하는 건지 조금 불안해요. 산소와 약이 왜 필요한지 쉽게 설명해 주시면 협조할게요…"

def doctor_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[의사 처방] {text}"}


def feedback_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[학습 안내] {text}"}


def hint_message(text: str) -> Dict[str, str]:
    """2회 이상 핵심 항목이 누락될 때 화면에 표시하는 표준화된 학습 힌트."""
    return safe_message({"role": "assistant", "content": f"[학습 힌트] {text}"})


def render_sbar_phone_window() -> None:
    """전화 아이콘을 눌렀을 때 열리는 SBAR 전용 보고창."""
    st.markdown("""
    <style>
    .sbar-phone-box {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 16px;
        padding: 18px 20px;
        margin: 14px 0 18px 0;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.10);
    }
    .sbar-phone-header {
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid #CBD5E1;
        padding-bottom: 10px;
        margin-bottom: 12px;
        color: #0F172A;
        font-weight: 850;
        font-size: 1.15rem;
    }
    .sbar-phone-caption {
        color: #475569;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-bottom: 8px;
    }
    </style>
    <div class="sbar-phone-box">
        <div class="sbar-phone-header">☎️ Physician Call | SBAR Report Window</div>
        <div class="sbar-phone-caption">
            이 창은 환자에게 말하는 대화창이 아니라, 의사에게 전화 보고하는 SBAR 전용 입력창입니다.
            Situation, Background, Assessment, Recommendation을 구분하여 작성한 뒤 보고를 제출하세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("sbar_phone_report_form", clear_on_submit=False):
        s_text = st.text_area(
            "S | Situation 현재 상황",
            value="",
            placeholder="예: 62세 남성 김심근 환자가 30분 전부터 흉통과 호흡곤란을 호소합니다.",
            height=80,
        )
        b_text = st.text_area(
            "B | Background 배경",
            value="",
            placeholder="예: 고혈압 과거력, 흡연력, 부친 심장마비 가족력이 있습니다.",
            height=80,
        )
        a_text = st.text_area(
            "A | Assessment 사정",
            value="",
            placeholder="예: NRS 8점 흉통, 좌측 어깨·턱·등으로 방사되는 통증, 식은땀, SpO₂ 93%, ECG상 II, III, aVF ST elevation, Troponin I 12.0 ng/mL 상승으로 AMI가 의심됩니다.",
            height=100,
        )
        r_text = st.text_area(
            "R | Recommendation 제안",
            value="",
            placeholder="예: 산소요법, 약물투여 및 추가 처방 확인을 요청드립니다.",
            height=80,
        )

        col_submit, col_close = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("📞 SBAR 보고 제출")
        with col_close:
            closed = st.form_submit_button("닫기")

        if submitted:
            if not all([s_text.strip(), b_text.strip(), a_text.strip(), r_text.strip()]):
                st.warning("S, B, A, R 항목을 모두 작성한 후 SBAR 보고를 제출하세요.")
            else:
                sbar_report = (
                    "SBAR 보고\n"
                    f"S: {s_text}\n"
                    f"B: {b_text}\n"
                    f"A: {a_text}\n"
                    f"R: {r_text}"
                )
                st.session_state.messages.append(safe_message({"role": "user", "content": f"☎️ [SBAR 보고]\n{sbar_report}"}))
                for answer in get_response(sbar_report):
                    st.session_state.messages.append(safe_message(answer))
                st.session_state.show_sbar_window = False
                st.rerun()

        if closed:
            st.session_state.show_sbar_window = False
            st.rerun()



def html_text(text: str) -> str:
    """대화 본문을 HTML 카드 안에 안전하게 넣기 위해 줄바꿈만 <br>로 바꾼다."""
    cleaned = clean_dialogue_text(text)
    return escape(cleaned).replace("\n", "<br>")


def render_chat_card(label: str, emoji: str, body: str, stage_label: str = "", card_type: str = "info") -> None:
    """색상 있는 대화 카드를 렌더링한다.

    중요:
    - 카드 틀은 HTML로 만들지만, 실제 대화 내용은 clean_dialogue_text()와 escape()를 거친다.
    - 따라서 이전 세션에 저장된 <div style=...> 조각이 대화 내용으로 노출되지 않는다.
    - 현재 단계 라벨과 대화 본문은 한 줄에 붙지 않고, 서로 분리되어 보이도록 구성한다.
    """
    palette = {
        "student": {"bg": "#E8F1FF", "border": "#4C8DFF", "title": "#0F172A", "text": "#1F2937"},
        "patient": {"bg": "#FFF4E6", "border": "#F59F00", "title": "#0F172A", "text": "#374151"},
        "system": {"bg": "#F1F5F9", "border": "#64748B", "title": "#0F172A", "text": "#334155"},
        "hint": {"bg": "#ECFDF5", "border": "#10B981", "title": "#064E3B", "text": "#065F46"},
        "complete": {"bg": "#F0FDF4", "border": "#22C55E", "title": "#14532D", "text": "#166534"},
        "default": {"bg": "#F8FAFC", "border": "#94A3B8", "title": "#0F172A", "text": "#334155"},
    }
    style = palette.get(card_type, palette["default"])

    safe_label = escape(clean_dialogue_text(label))
    safe_stage = escape(clean_dialogue_text(stage_label)) if stage_label else ""
    safe_body = html_text(body)

    stage_html = ""
    if safe_stage:
        stage_html = (
            f"<div style=\"margin-top:12px; margin-bottom:12px;\">"
            f"<span style=\"display:inline-block; background:#FFFFFFAA; border:1px solid {style['border']}; "
            f"color:{style['title']}; border-radius:999px; padding:5px 12px; "
            f"font-size:1.02rem; font-weight:800; line-height:1.4;\">"
            f"📍 현재 단계: {safe_stage}"
            f"</span></div>"
        )

    # 본문은 단계 표시와 분리되도록 별도 block으로 배치한다.
    body_html = ""
    if safe_body:
        body_html = (
            f"<div style=\"margin-top:10px; padding-top:2px; color:{style['text']}; "
            f"font-size:1.22rem; line-height:1.75; word-break:keep-all; overflow-wrap:anywhere;\">"
            f"{safe_body}"
            f"</div>"
        )

    card_html = (
        f"<div style=\"width:100%; box-sizing:border-box; background:{style['bg']}; "
        f"border-left:7px solid {style['border']}; border-radius:14px; "
        f"padding:24px 28px; margin:14px 0 20px 0; min-height:96px; "
        f"box-shadow:0 1px 3px rgba(15,23,42,0.10);\">"
        f"<div style=\"font-weight:900; color:{style['title']}; font-size:1.28rem; line-height:1.5;\">"
        f"{escape(emoji)} {safe_label}"
        f"</div>"
        f"{stage_html}"
        f"{body_html}"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_message(msg: Dict[str, str]) -> None:
    """챗봇, 학습자, 시스템 정보를 넓은 색상 카드로 표시한다.

    v16 수정:
    - st.info/st.warning 기본 알림 대신 안전한 custom card를 사용해 카드 높이와 여백을 키웠다.
    - 실제 대화 내용은 반드시 clean_dialogue_text()와 escape()를 거쳐 HTML 코드가 보이지 않게 했다.
    - 환자 메시지의 현재 단계 라벨과 대화 내용을 한 줄에 붙이지 않고, 단계 라벨 아래에 본문을 따로 표시한다.
    """
    msg = sanitize_message_for_display(msg)
    raw = str(msg.get("content", ""))
    role = msg.get("role", "assistant")

    # 환자 확인 메시지는 내부 진행상태 체크용으로만 사용하고 화면에는 표시하지 않는다.
    if raw.startswith("[환자확인]"):
        return

    label = "안내"
    body = raw
    emoji = "ℹ️"
    stage_label = ""
    card_type = "default"

    # 학습자 입력
    if role == "user":
        label = "학생간호사"
        emoji = "🧑‍⚕️"
        card_type = "student"
        body = clean_dialogue_text(raw)

    # 챗봇 환자 응답
    elif raw.startswith("[환자]"):
        label = "챗봇 환자 김심근"
        emoji = "🫀"
        card_type = "patient"
        body = raw.replace("[환자]", "", 1).strip()
        if body.startswith("[현재 단계:"):
            first_line, sep, remaining_body = body.partition("\n")
            stage_label = first_line.replace("[현재 단계:", "", 1).rstrip("]").strip()
            body = remaining_body if sep else ""
        body = clean_dialogue_text(body)

    # 시스템: 환자 확인은 표시하지 않음
    elif raw.startswith("[환자확인]"):
        return

    # 시스템: 활력징후
    elif raw.startswith("[활력징후]"):
        label = "시스템 | 활력징후"
        emoji = "📊"
        card_type = "system"
        body = clean_dialogue_text(raw.replace("[활력징후]", "", 1).strip())

    # 시스템: 검사결과
    elif raw.startswith("[검사결과]"):
        label = "시스템 | 검사결과"
        emoji = "🧪"
        card_type = "system"
        body = clean_dialogue_text(raw.replace("[검사결과]", "", 1).strip())

    # 시스템: 의사 처방
    elif raw.startswith("[의사 처방]"):
        label = "시스템 | 의사 처방"
        emoji = "💊"
        card_type = "system"
        body = clean_dialogue_text(raw.replace("[의사 처방]", "", 1).strip())

    # 시뮬레이션 완료 안내
    elif raw.startswith("[완료 안내]"):
        label = "시뮬레이션 완료"
        emoji = "✅"
        card_type = "complete"
        body = clean_dialogue_text(raw.replace("[완료 안내]", "", 1).strip())

    # 기존 [시스템] 메시지 중 객관적 임상자료는 표시하고, 진행 조건 안내는 숨김
    elif raw.startswith("[시스템]"):
        system_body = raw.replace("[시스템]", "", 1).strip()

        if system_body.startswith("환자 확인") or "등록번호" in system_body or "팔찌" in system_body:
            return
        elif "5분 후" in system_body or "재사정" in system_body:
            label = "시스템 | 재사정 안내"
            emoji = "⏱️"
            card_type = "system"
            body = clean_dialogue_text(system_body)
        elif system_body.startswith("의사 처방") or "O₂" in system_body or "NTG" in system_body or "Aspirin" in system_body:
            label = "시스템 | 의사 처방"
            emoji = "💊"
            card_type = "system"
            body = clean_dialogue_text(system_body)
        elif system_body.startswith("초기 활력징후") or "BP:" in system_body or "SpO₂" in system_body:
            label = "시스템 | 활력징후"
            emoji = "📊"
            card_type = "system"
            body = clean_dialogue_text(system_body)
        elif system_body.startswith("검사결과") or "Troponin" in system_body or "CK-MB" in system_body:
            label = "시스템 | 검사결과"
            emoji = "🧪"
            card_type = "system"
            body = clean_dialogue_text(system_body)
        else:
            return

    # 표준화된 학습 힌트
    elif raw.startswith("[학습 힌트]"):
        label = "학습 힌트"
        emoji = "💡"
        card_type = "hint"
        body = clean_dialogue_text(raw.replace("[학습 힌트]", "", 1).strip())

    # 학습 안내는 표시하지 않음
    elif raw.startswith("[학습 안내]"):
        return

    else:
        body = clean_dialogue_text(raw)

    # 마지막 안전장치: 출력 직전 본문 정리
    body = clean_dialogue_text(body)
    stage_label = clean_dialogue_text(stage_label)
    render_chat_card(label=label, emoji=emoji, body=body, stage_label=stage_label, card_type=card_type)

def get_current_guidance() -> str:
    """처음 문구를 반복하지 않고 현재 단계에 맞는 재질문/안내를 제공한다."""
    if not st.session_state.intro_done:
        return "먼저 자기소개 후 이름과 등록번호 또는 팔찌를 확인하고, 주호소와 정서 상태를 확인해보세요. 예: ‘안녕하세요, 담당 간호학생입니다. 정확한 확인을 위해 성함과 등록번호 또는 팔찌를 확인하겠습니다. 지금 어디가 가장 불편하신가요?’"
    if not st.session_state.pain_symptom_done:
        return "현재 단계에서는 통증 위치, 양상, 시작 시점, NRS 점수, 방사통, 호흡곤란·식은땀·불안, 악화요인과 완화요인을 확인해보세요."
    if not st.session_state.vitals_done:
        return "다음으로 활력징후를 확인해보세요. 예: ‘현재 활력징후를 확인하겠습니다.’"
    if not st.session_state.history_risk_done:
        return "과거력, 복용약, 흡연력, 가족력, 알레르기 여부, 최근 항응고제/항혈소판제 복용 여부와 출혈성 질환 여부를 확인해보세요."
    if not st.session_state.ami_judged:
        return "수집한 자료를 바탕으로 AMI 가능성을 판단하고, 심전도와 심근효소 검사의 필요성을 인식해보세요."
    if not st.session_state.exam_explained:
        return "심전도와 혈액검사가 왜 필요한지 설명하고, 환자의 이해와 검사 참여 의사를 확인해보세요."
    if not st.session_state.labs_shown:
        return "검사 설명과 참여 확인이 완료되었습니다. 이제 검사결과를 확인해보세요."
    if not st.session_state.interaction_completed:
        return "검사결과를 바탕으로 환자 문제를 확인하고, 통증 완화·호흡곤란 감소·불안 감소를 공동 목표로 설정한 뒤, 산소요법과 약물치료, 심전도 재확인, 막힌 혈관 확인과 빠른 치료를 위한 관상동맥조영술 준비가 필요할 수 있음을 환자에게 쉽게 설명해보세요."
    if not st.session_state.sbar_reported:
        return "SBAR 형식으로 환자 상태, 배경, 사정 결과, 제안을 포함하여 의사에게 보고해보세요."
    if not st.session_state.intervention_explained:
        return "의사 처방을 바탕으로 산소요법, NTG, Aspirin, Plavix, ECG 재확인 및 CAG preparation의 필요성을 설명하고, 환자의 이해와 참여 의사를 확인해보세요."
    if not st.session_state.intervention_done:
        return "이제 처방에 따라 산소요법, NTG, Aspirin, Plavix, ECG monitoring 유지, 12-lead ECG 재확인 및 CAG preparation을 수행해보세요."
    if not st.session_state.reassessment_done:
        return "중재 후 통증 완화 여부, 호흡곤란 감소 여부, 불안 감소 여부를 확인하고, 처음 함께 설정한 목표가 달성되었는지 확인해보세요."
    return "시뮬레이션 흐름은 완료되었습니다. 디브리핑에서 수행 과정을 성찰해보세요."


STEP_HELP: Dict[str, Tuple[str, str]] = {
    "1. 지각: 초기 접촉 및 주호소 확인": (
        "인사하고 환자를 확인한 뒤, 가장 불편한 증상을 묻습니다.",
        "이름·등록번호/팔찌 확인 + 주호소 확인"
    ),
    "2. 지각: 통증 및 동반 증상 사정": (
        "가슴 통증과 함께 나타나는 증상을 확인합니다.",
        "통증 위치·양상·시작시점·NRS·방사통·호흡곤란·식은땀·불안 확인"
    ),
    "3. 지각: 활력징후 확인": (
        "활력징후를 측정하겠다고 말합니다.",
        "혈압·맥박·호흡·산소포화도·체온 확인 요청"
    ),
    "4. 지각: 병력 및 위험요인 사정": (
        "과거력, 복용약, 가족력 등 위험요인을 확인합니다.",
        "고혈압·복용약·흡연·가족력·알레르기·항응고제/항혈소판제·출혈성 질환 확인"
    ),
    "5. 판단: 심혈관질환 의심 상황 판단 및 검사 필요성 인식": (
        "심장 문제 가능성을 판단하고, 심전도와 혈액검사가 필요함을 설명합니다.",
        "심근경색 또는 심장 문제가 의심된다고 말하고, 심전도와 혈액검사 필요성 설명"
    ),
    "6. 행위/반응: 검사 필요성 설명 및 환자의 이해·참여 확인": (
        "심전도와 혈액검사가 왜 필요한지 쉽게 설명합니다.",
        "심전도 설명 + 혈액검사 설명 + 검사 진행 확인"
    ),
    "7. 상호작용: 검사결과 기반 문제 구체화": (
        "검사결과를 확인하고 환자 문제를 정리합니다.",
        "검사결과 확인 후 주요 문제 파악"
    ),
    "8. 상호작용: 간호목표 공유 및 목표달성 방법 확인": (
        "문제, 목표, 치료 방법을 환자와 공유합니다.",
        "문제 확인 + 목표 공유 + 산소·약물·심전도 재확인·CAG 준비 설명 + 협조 확인"
    ),
    "9. 교류작용: SBAR 보고 및 처방 확인": (
        "의사에게 SBAR 형식으로 보고합니다.",
        "S·B·A·R 내용을 포함하여 보고"
    ),
    "10. 교류작용: 중재 설명 및 중재 수행": (
        "처방된 산소와 약물, 검사/시술 준비를 설명하고 수행합니다.",
        "산소·약물 설명 + 불편감 안내 + 동의 확인 + 처방 수행"
    ),
    "11. 목표달성: 중재 후 재사정 및 목표달성 확인": (
        "중재 후 증상이 좋아졌는지 다시 확인합니다.",
        "통증 감소 + 호흡곤란 완화 + 불안 감소 확인"
    ),
    "12. 성찰: 디브리핑": (
        "수행한 과정을 돌아보고 답변을 작성합니다.",
        "디브리핑 질문 작성"
    ),
}


# ------------------------------------------------------------
# 8. OpenAI 말투 자연화: 환자 역할만 허용
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
5. 전문용어를 먼저 사용하지 말고, 환자가 실제로 느끼는 증상 중심으로 말하세요.
6. 너무 반듯한 문장보다 실제 응급실 환자처럼 불안하고 힘든 말투로 답하세요.
7. 가능한 경우 답변에는 다음 요소 중 2개 이상을 자연스럽게 포함하세요: 현재 느끼는 증상, 불안/두려움, 학생에게 묻는 짧은 질문, 검사·중재에 대한 걱정 또는 협조 의사.
8. 답변은 1~3문장으로 하되, 말끝은 자연스럽게 흐릴 수 있습니다.
9. 예: “가슴이 너무 조여요… 숨도 좀 차고요. 저 정말 괜찮은 건가요?
”"""

    prompt = f"""
학생 입력:
{user_input}

핵심 정보:
{clinical_fact}

핵심 정보를 유지하면서 실제 응급실 환자처럼 자연스럽고 불안한 말투로 한국어로 답하세요.
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
# 9. 누적 인식 업데이트 함수
# ------------------------------------------------------------
def update_exam_explanation_state(text: str) -> List[str]:
    """검사 설명 단계의 핵심 항목을 한 번의 입력에서 동시에 누적 인식한다.

    변경 사항
    - 학생이 한 문장 안에서 심전도 설명, 혈액검사 설명, 검사 참여 확인을 함께 말하면
      세 항목을 동시에 체크한다.
    - 지나치게 제한적인 키워드 때문에 같은 질문이 반복되지 않도록 표현 범위를 넓혔다.
    - 단순 검사명 나열은 설명 완료로 보지 않고, 검사 목적이 함께 들어온 경우를 우선 인정한다.
    """
    updates: List[str] = []

    ecg_name_keywords = [
        "심전도", "심전도 검사", "ecg", "ekg", "12유도", "12 유도", "12-lead",
        "electrocardiogram", "electrocardiography"
    ]
    ecg_explain_keywords = [
        "심장 전기", "전기적 변화", "전기 신호", "전기 활동", "전기 흐름",
        "심장 리듬", "리듬", "심장 박동", "박동", "맥박 리듬",
        "심장 상태", "심장 확인", "심장이 잘", "심장이 제대로", "심장 기능",
        "심장 문제", "원인 파악", "원인을 파악", "상태를 확인", "상태 확인",
        "heart condition", "heart status", "electrical changes", "electrical activity",
        "heart rhythm", "heart signal"
    ]

    blood_name_keywords = [
        "혈액검사", "혈액 검사", "피검사", "피 검사", "채혈", "심근효소", "심장효소", "심장 효소",
        "blood test", "blood work", "cardiac enzyme", "myocardial enzyme"
    ]
    blood_damage_purpose_keywords = [
        "심장근육 손상", "심장 근육 손상", "심근 손상", "심장 손상", "손상 여부",
        "심장 손상 여부", "심근 손상 여부", "심장근육 손상 여부",
        "심근경색 여부", "심장 문제가 있는지", "심장 문제인지", "심장에 문제가 있는지",
        "heart muscle damage", "myocardial damage", "cardiac muscle damage",
        "damage to the heart muscle", "damage of the heart muscle"
    ]
    blood_marker_keywords = [
        "트로포닌", "troponin", "ck-mb", "ckmb", "심장 관련 수치", "심장수치", "심장 수치",
        "심장 손상 지표", "심장 지표", "심근효소 수치", "심장 효소 수치", "효소 수치"
    ]
    blood_marker_purpose_keywords = [
        "수치", "수치 확인", "확인", "측정", "검출", "상승", "올라", "증가",
        "level", "levels", "check", "measure", "measurement", "detect", "determine"
    ]
    blood_vague_but_acceptable_keywords = [
        "심장 관련 수치", "심장 수치", "심장수치", "심장 손상 지표", "심장 지표",
        "심근효소 수치", "심장 효소 수치", "심장근육 손상 여부", "심장 손상 여부"
    ]

    cooperation_keywords = [
        "협조", "협조 요청", "협조해 주실 수", "협조해주시겠", "협조해 주시겠",
        "동의", "동의하시", "동의하시면", "괜찮을까요", "괜찮으실까요",
        "진행해도", "진행해도 될까요", "진행해도 괜찮", "검사해도 될까요",
        "검사를 진행", "검사 진행", "검사하겠습니다", "검사 하겠습니다",
        "진행하겠습니다", "진행 하겠습니다", "진행할게요", "바로 진행", "지금 진행",
        "바로 가능합니다", "가능합니다", "바로 해드리겠습니다", "바로 해드릴게요",
        "검사 결과 확인", "검사결과 확인", "결과 확인", "시행해도",
        "설명 들었으면", "이해되셨으면", "이해하셨다면", "해도 될까요",
        "cooperate", "cooperation", "agree", "consent", "proceed",
        "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]

    ecg_explained_now = has_any(text, ecg_name_keywords) and has_any(text, ecg_explain_keywords)

    blood_has_damage_purpose = (
        has_any(text, blood_name_keywords)
        and has_any(text, blood_damage_purpose_keywords)
    )
    blood_has_marker_purpose = (
        has_any(text, blood_marker_keywords)
        and has_any(text, blood_marker_purpose_keywords)
    )
    blood_has_vague_but_acceptable_purpose = has_any(text, blood_vague_but_acceptable_keywords)

    if ecg_explained_now and not st.session_state.ecg_explained:
        st.session_state.ecg_explained = True
        updates.append("심전도 검사 설명")

    if (blood_has_damage_purpose or blood_has_marker_purpose or blood_has_vague_but_acceptable_purpose) and not st.session_state.blood_test_explained:
        st.session_state.blood_test_explained = True
        updates.append("혈액검사 설명")

    # 같은 입력 안에서 심전도와 혈액검사 설명이 새로 완료된 뒤에도 협조 확인을 동시에 인정한다.
    if (
        st.session_state.ecg_explained
        and st.session_state.blood_test_explained
        and (has_any(text, cooperation_keywords) or is_exam_cooperation_response(text))
        and not st.session_state.exam_cooperation_requested
    ):
        st.session_state.exam_cooperation_requested = True
        updates.append("검사 참여 확인")

    if (
        st.session_state.ecg_explained
        and st.session_state.blood_test_explained
        and st.session_state.exam_cooperation_requested
    ):
        st.session_state.exam_explained = True
        st.session_state.cooperation_formed = True
        st.session_state.exam_error_count = 0
        mark_checklist("6. 행위/반응: 검사 필요성 설명 및 환자의 이해·참여 확인")

    return updates


def update_interaction_state(text: str) -> List[str]:
    """상호작용 단계의 핵심 항목을 한 번의 입력에서 동시에 누적 인식한다.

    변경 사항
    - 이전 버전처럼 현재 필요한 1개 항목만 체크하고 return하지 않는다.
    - 학생이 한 문장 안에서 문제 확인, 목표 공유, 목표달성 방법, 이해·참여 확인을 함께 말하면
      가능한 항목을 모두 동시에 체크한다.
    - 목표달성 방법은 내부적으로 산소요법, 약물치료, 심전도 재확인, 관상동맥조영술 준비 가능성
      4개가 모두 인식되었을 때 완료된다.
    """
    updates: List[str] = []

    problem_keywords = [
        "문제", "현재 문제", "가장 힘든", "가장 큰 문제", "우선 문제", "주요 문제",
        "가슴 통증", "가슴통증", "흉통", "가슴 답답", "답답", "방사통",
        "숨찬", "숨참", "호흡곤란", "호흡 곤란", "불안", "불안 정도",
        "검사결과", "검사 결과", "결과 토대로", "결과를 보면", "환자 상태", "상태 판단",
        "의미있는 자료", "의미 있는 자료", "st 상승", "트로포닌", "ck-mb",
        "심근경색", "급성심근경색", "급성 심근경색", "ami", "stemi",
        "acute myocardial infarction", "myocardial infarction", "heart attack",
        "suspected myocardial infarction", "suspected heart attack"
    ]
    goal_keywords = [
        "목표", "공동 목표", "함께 목표", "우선 목표", "치료 목표", "간호 목표",
        "통증을 줄", "통증 감소", "통증 완화", "흉통 완화", "가슴 통증 완화",
        "숨쉬기 편", "숨 쉬기 편", "호흡을 편", "호흡곤란 완화", "호흡곤란 감소", "숨찬 증상 완화",
        "불안을 줄", "불안 완화", "불안 감소", "안정", "안심"
    ]

    oxygen_method_keywords = [
        "산소", "산소요법", "산소 요법", "산소 공급", "산소공급", "산소를 공급",
        "콧줄", "비강캐뉼라", "비강 캐뉼라", "o2", "o₂", "oxygen"
    ]
    medication_method_keywords = [
        "약물", "약물치료", "약물 치료", "약물 투여", "약", "투약",
        "니트로", "니트로글리세린", "ntg",
        "아스피린", "aspirin", "플라빅스", "plavix",
        "클로피도그렐", "clopidogrel", "혈전", "통증 조절", "medication", "medicine", "drug"
    ]
    ecg_recheck_method_keywords = [
        "심전도 재확인", "심전도 다시", "심전도를 다시", "심전도도 다시",
        "심전도 재검", "심전도 재검사", "심전도 확인", "심전도를 확인",
        "심장 리듬 확인", "심장 리듬을 다시", "ecg monitoring", "ekg monitoring",
        "심전도 모니터링", "모니터링", "12-lead ecg re-check",
        "12-lead ecg recheck", "ecg re-check", "ecg recheck",
        "ekg re-check", "ekg recheck"
    ]
    cag_method_keywords = [
        "관상동맥조영술", "관상동맥 조영술", "혈관조영술", "혈관 조영술", "조영술",
        "cag", "cag preparation", "cag 준비", "조영술 준비",
        "막힌 혈관", "막힌 혈관 확인", "혈관 확인", "혈관을 확인", "혈관검사", "혈관 검사",
        "관상동맥 검사", "빠른 치료", "시술 준비", "coronary angiography"
    ]

    agreement_keywords = [
        "협조", "환자 협조", "협조 요청", "협조해 주실 수", "협조해주시겠", "협조해 주시겠",
        "치료에 협조", "방법에 협조", "함께 해", "같이 해",
        "동의", "동의하시", "동의하시면", "괜찮을까요", "괜찮으실까요",
        "진행해도", "진행해도 괜찮", "진행해도 될까요", "해도 될까요", "진행하시", "진행하시겠", "진행 하시","진행 하시겠",
        "이 방법으로", "이렇게 진행", "이해되셨나요", "이해하셨나요", "이해되시나요",
        "설명드린 내용", "cooperate", "cooperation", "agree", "consent", "proceed",
        "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]

    if has_any(text, problem_keywords) and not st.session_state.problem_identified:
        st.session_state.problem_identified = True
        updates.append("환자 문제 확인")

    # v30: '목표'라는 단어만으로는 간호목표 공유를 완료하지 않는다.
    # 통증 완화, 호흡곤란 감소, 불안 감소/안정처럼 실제 임상 목표가 포함될 때만 인정한다.
    if is_valid_interaction_goal_statement(text) and not st.session_state.goal_set:
        st.session_state.goal_set = True
        updates.append("간호목표 공유")

    if has_any(text, oxygen_method_keywords):
        st.session_state.interaction_oxygen_method_explained = True
    if has_any(text, medication_method_keywords):
        st.session_state.interaction_medication_method_explained = True
    if has_any(text, ecg_recheck_method_keywords):
        st.session_state.interaction_ecg_recheck_method_explained = True
    if has_any(text, cag_method_keywords):
        st.session_state.interaction_cag_method_explained = True

    if (
        st.session_state.interaction_oxygen_method_explained
        and st.session_state.interaction_medication_method_explained
        and st.session_state.interaction_ecg_recheck_method_explained
        and st.session_state.interaction_cag_method_explained
        and not st.session_state.means_explained
    ):
        st.session_state.means_explained = True
        updates.append("목표달성 방법 설명")

    if has_any(text, agreement_keywords) and not st.session_state.agreement_obtained:
        st.session_state.agreement_obtained = True
        updates.append("이해·참여 확인")

    if (
        st.session_state.problem_identified
        and st.session_state.goal_set
        and st.session_state.means_explained
        and st.session_state.agreement_obtained
    ):
        st.session_state.interaction_completed = True
        st.session_state.cooperation_formed = True
        st.session_state.interaction_error_count = 0
        mark_checklist("8. 상호작용: 간호목표 공유 및 목표달성 방법 확인")

    return updates


def update_intervention_explanation_state(text: str) -> List[str]:
    """중재 설명 단계의 핵심 항목을 한 번의 입력에서 동시에 누적 인식한다.

    v26 최종 수정
    - 힌트는 새 핵심 항목 없이 2회 연속 막힌 경우에만 제시한다.
    - 약물 설명은 단순히 "약이 통증을 줄인다"만으로 완료하지 않는다.
      NTG/니트로글리세린 등 흉통 완화 목적과 Aspirin/Plavix 등 혈전 예방 목적이 모두 확인될 때 완료한다.
    - 이상반응/불편감 안내는 증상 표현과 대처 행동이 함께 있을 때만 인정한다.
      예: "어지럽거나 두통, 출혈, 불편감이 있으면 바로 말씀하거나 콜벨을 눌러주세요."
    - 동의/협조 확인은 산소, 약물, 목적, 이상반응/불편감 안내가 모두 충족된 뒤에만 인정한다.
    """
    updates: List[str] = []

    oxygen_name_keywords = [
        "산소", "산소요법", "산소 요법", "산소 투여", "산소 적용", "o2", "o₂",
        "비강캐뉼라", "비강 캐뉼라", "nasal cannula", "oxygen"
    ]
    oxygen_explain_keywords = [
        "숨쉬기", "숨 쉬기", "호흡", "호흡곤란", "숨찬", "숨 차", "산소포화도",
        "산소 공급", "산소공급", "심장에 산소", "심장 산소", "심장 부담", "부담을 줄",
        "완화", "도움", "편하게", "편해", "숨을 쉬", "breathing", "shortness of breath",
        "supply oxygen", "oxygen supply", "help the heart", "strain on the heart", "relieve", "ease breathing"
    ]

    medication_general_keywords = [
        "약", "약물", "투약", "medicine", "medication", "drug"
    ]
    pain_med_name_keywords = [
        "니트로", "니트로글리세린", "ntg", "nitroglycerin", "모르핀", "morphine"
    ]
    pain_med_purpose_keywords = [
        "통증", "흉통", "가슴 통증", "가슴통증", "통증 완화", "통증 감소", "통증 조절",
        "아픈 것", "아픈 증상", "chest pain", "pain", "relieve pain", "reduce pain", "pain relief"
    ]

    clot_med_name_keywords = [
        "아스피린", "aspirin", "플라빅스", "plavix", "클로피도그렐", "clopidogrel",
        "항혈소판", "항 혈소판"
    ]
    clot_med_purpose_keywords = [
        "혈전", "피떡", "혈전 예방", "혈전 생성", "혈전 생성을", "혈전이 생기는",
        "막힌 혈관", "혈관이 막", "혈류", "clot", "blood clot", "prevent clot",
        "reduce clot", "antiplatelet"
    ]
    prevention_action_keywords = [
        "예방", "막", "줄", "줄이", "감소", "방지", "도움", "prevent", "reduce", "decrease", "help"
    ]

    purpose_keywords = [
        "통증", "흉통", "가슴 통증", "호흡곤란", "숨쉬기", "숨 쉬기", "숨찬",
        "완화", "줄", "감소", "도움", "편하게", "심장 부담", "혈전 예방", "혈관 확장", "혈류",
        "chest pain", "shortness of breath", "breathing", "relieve", "reduce", "help",
        "strain on the heart", "blood clot"
    ]

    side_effect_symptom_keywords = [
        "어지럽", "어지러움", "두통", "출혈", "멍", "구토", "불편", "불편감", "이상", "부작용",
        "통증 악화", "통증이 심", "호흡곤란", "숨이 더 차", "숨 더 차",
        "dizzy", "dizziness", "headache", "bleeding", "bruise", "uncomfortable",
        "discomfort", "side effect", "worsening pain", "difficulty breathing"
    ]
    side_effect_action_keywords = [
        "말씀", "알려", "호출벨", "콜벨", "콜밸", "벨", "호출", "간호사 부르", "간호사를 부르",
        "저희를 부르", "불러주세요", "불러 주세요", "눌러주세요", "눌러 주세요", "눌러서",
        "바로 부르", "바로 말", "바로 말씀", "바로 알려", "즉시 말씀",
        "tell me", "let me know", "notify", "call bell", "call the nurse", "press the bell", "right away"
    ]

    cooperation_keywords = [
        "협조", "협조해 주실 수", "협조해주시겠", "협조해 주시겠", "협조 부탁",
        "동의", "동의하시", "동의하시나요", "동의해주세요", "동의해 주세요", "동의하시면", "동의해주시면",
        "괜찮을까요", "괜찮으실까요", "괜찮으시면", "괜찮다면",
        "진행해도", "진행해도 괜찮", "진행해도 될까요", "진행하겠습니다", "바로 진행",
        "시작하겠습니다", "해도 될까요", "이 방법으로", "이렇게 진행",
        "cooperate", "cooperation", "agree", "consent", "proceed",
        "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]

    oxygen_explained_now = has_any(text, oxygen_name_keywords) and has_any(text, oxygen_explain_keywords)

    # 약물 설명은 두 축으로 나누어 누적 인식한다.
    # 1) NTG/니트로글리세린 등 흉통 완화 목적
    # 2) Aspirin/Plavix 등 혈전 예방 목적
    pain_med_explained_now = (
        has_any(text, pain_med_name_keywords)
        and has_any(text, pain_med_purpose_keywords)
    )
    clot_med_explained_now = (
        has_any(text, clot_med_name_keywords)
        and has_any(text, clot_med_purpose_keywords)
        and has_any(text, prevention_action_keywords)
    )

    if oxygen_explained_now and not st.session_state.oxygen_explained:
        st.session_state.oxygen_explained = True
        updates.append("산소요법 설명")

    if pain_med_explained_now and not st.session_state.get("medication_pain_relief_explained", False):
        st.session_state.medication_pain_relief_explained = True

    if clot_med_explained_now and not st.session_state.get("medication_clot_prevention_explained", False):
        st.session_state.medication_clot_prevention_explained = True

    medication_explained_now = (
        st.session_state.get("medication_pain_relief_explained", False)
        and st.session_state.get("medication_clot_prevention_explained", False)
    )

    if medication_explained_now and not st.session_state.medication_explained:
        st.session_state.medication_explained = True
        updates.append("약물투여 설명")

    # 목적 설명은 산소 설명 또는 약물 설명/부분 설명과 함께 들어오거나,
    # 이미 관련 설명이 된 뒤 목적 표현이 들어오면 인정한다.
    if (
        (
            oxygen_explained_now
            or st.session_state.oxygen_explained
            or pain_med_explained_now
            or clot_med_explained_now
            or st.session_state.medication_explained
        )
        and has_any(text, purpose_keywords)
        and not st.session_state.intervention_purpose_explained
    ):
        st.session_state.intervention_purpose_explained = True
        updates.append("중재 목적 설명")

    # 이상반응/불편감 안내 인식
    # 1) 원칙적으로는 증상 표현 + 대처 행동이 함께 있을 때 인정한다.
    # 2) 단, 환자가 직전 흐름에서 “어지럽거나 불편하면 어떻게 해야 하나요?”라고 묻는 단계
    #    즉 산소·약물·목적 설명은 끝났고 이상반응 안내만 남은 상태에서는,
    #    학생이 “바로 말씀하세요/콜벨을 누르세요”처럼 대처 행동만 답해도 맥락상 인정한다.
    #    이렇게 해야 같은 힌트가 반복 제시되지 않고 다음 동의 확인 단계로 진행된다.
    side_effect_action_now = has_any(text, side_effect_action_keywords)
    side_effect_symptom_now = has_any(text, side_effect_symptom_keywords)
    awaiting_side_effect_guidance = (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and not st.session_state.side_effect_guidance_given
    )
    side_effect_guidance_now = side_effect_action_now and (
        side_effect_symptom_now or awaiting_side_effect_guidance
    )
    if side_effect_guidance_now and not st.session_state.side_effect_guidance_given:
        st.session_state.side_effect_guidance_given = True
        updates.append("이상반응/불편감 안내")

    # 중재 참여 확인은 산소·약물·목적·이상반응/불편감 안내가 모두 이루어진 뒤에만 인정한다.
    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and st.session_state.side_effect_guidance_given
        and (has_any(text, cooperation_keywords) or is_intervention_cooperation_response(text))
        and not st.session_state.intervention_cooperation_requested
    ):
        st.session_state.intervention_cooperation_requested = True
        updates.append("중재 참여 확인")

    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and st.session_state.side_effect_guidance_given
        and st.session_state.intervention_cooperation_requested
    ):
        st.session_state.intervention_explained = True
        st.session_state.intervention_error_count = 0

    return updates


# ------------------------------------------------------------
# 10. 입력 분류
# ------------------------------------------------------------
def classify_input(user_text: str) -> str:
    """
    분류 원칙:
    1) 병력 확인은 활력징후 확인보다 먼저 분류하여 '고혈압 있으세요?' 오류를 방지한다.
    2) 검사 설명, 상호작용, 중재 설명은 누적 인식을 위해 별도 category로 보낸다.
    3) 중재 수행은 처방 확인 및 중재 설명 후에만 수행된다.
    4) 재사정은 중재 완료 후에만 인정된다.
    """
    text = user_text.lower().strip()

    # 중재 수행 후에는 재사정 단계로 고정한다.
    # 같은 "통증/숨/불안" 표현이 들어와도 초기 통증 사정으로 되돌아가지 않도록
    # 입력 분류의 가장 앞에서 처리한다.
    if st.session_state.get("intervention_done", False) and not st.session_state.get("reassessment_done", False):
        if is_post_intervention_vitals_request(text):
            return "post_intervention_vitals"
        if is_reassessment_input(text):
            return "reassessment"
        # 모호한 입력도 초기 단계로 보내지 않고 재사정 고정 반응으로 처리한다.
        return "reassessment"

    # 초기 접촉/환자확인 분류
    # 주의: 기존의 "정확한 확인"은 검사 필요성 설명 문장
    # (예: "정확한 확인을 위해 심전도와 혈액검사가 필요합니다")까지
    # 환자확인 단계로 잘못 분류하여 김심근 등록번호 응답이 반복되는 문제가 있었다.
    # 따라서 환자확인은 성함·등록번호·팔찌·본인확인처럼 환자확인 의도가 명확한 표현만 인정한다.
    intro_keywords = [
        "안녕하세요", "학생간호사", "간호학생", "담당 간호사", "담당 학생",
        "제가 도와드리겠습니다", "제가 사정하겠습니다",
        "성함이 어떻게 되세요", "이름이 어떻게 되세요", "환자분 성함", "김심근님 맞으세요",
        "등록번호", "등록 번호", "환자번호", "환자 번호", "팔찌", "환자 팔찌", "손목밴드",
        "정확한 환자 확인", "정확한 본인 확인", "본인 확인", "환자 확인",
        "identification", "patient identification", "id band", "wristband"
    ]
    if has_any(text, intro_keywords):
        return "intro"

    # 재사정은 중재 후에만 우선 인정
    reassess_keywords = [
        "재사정", "다시 확인", "상태를 다시", "치료 후", "중재 후", "처치 후",
        "통증 변화", "통증 감소", "지금 통증", "통증은 지금", "현재통증", "현재 통증",
        "가슴통증 몇 점", "가슴 통증 몇 점", "몇 점", "nrs", "통증척도",
        "호흡 상태", "호흡은", "숨쉬기", "숨 쉬기", "숨 쉬는 건 괜찮", "지금 숨", "현재 숨",
        "숨쉬는 건 괜찮", "호흡곤란", "호흡 곤란", "불편감",
        "불안 정도", "불안은", "불안감", "불안 완화", "불안 감소", "지금 불안", "현재 불안",
        "어떠세요", "나아졌", "완화",
        "활력징후", "활력 징후", "혈압", "맥박", "호흡수", "산소포화도",
        "목표 달성", "목표가 달성", "함께 설정한 목표", "처음 설정한 목표",
        "통증 완화 목표", "호흡곤란 감소 목표", "불안 감소 목표",
        "가장 불편", "가장 걱정", "아직 불편", "아직 걱정",
        "계속 관찰", "계속 모니터링",
        "reassess", "re-assess", "after treatment", "after intervention",
        "after medication", "after mediation", "check back", "rate your chest pain",
        "chest pain", "pain relief", "pain score", "scale of 0 to 10",
        "breathing", "breathe", "breathing easier", "shortness of breath",
        "dyspnea", "difficulty breathing", "anxiety", "anxious",
        "anxiety decreased", "vital signs", "blood pressure", "pulse",
        "respiratory rate", "oxygen saturation", "spo2", "goal achieved"
    ]
    if st.session_state.intervention_done and has_any(text, reassess_keywords):
        return "reassessment"

    closing_keywords = [
        "바로 말씀", "말씀해주세요", "말씀해 주세요", "알려주세요", "알려 주세요",
        "계속 관찰", "계속 살피", "옆에 있겠습니다", "상태가 변하면", "통증이 심해지면",
        "답답해지면", "불편하면 말씀", "불편하면 알려", "계속 확인하겠습니다", 
    ]
    if st.session_state.intervention_done and has_any(text, closing_keywords):
        return "closing_therapeutic"

    # 검사 설명은 끝났고 검사 참여 확인만 남은 경우, 짧은 진행 표현도
    # 검사 설명 단계로 보내 검사 참여 확인으로 처리한다.
    # 예: “네”, “바로 가능합니다”, “검사 진행하겠습니다”, “검사 결과를 확인하겠습니다”, “I will check the test results”.
    # 단, 심전도와 혈액검사 설명이 모두 완료된 상태에서만 적용해
    # 설명 없이 검사를 진행하는 오류를 막는다.
    if (
        not st.session_state.exam_explained
        and st.session_state.ecg_explained
        and st.session_state.blood_test_explained
        and not st.session_state.exam_cooperation_requested
        and is_exam_cooperation_response(text)
    ):
        return "exam_explanation"

    # ------------------------------------------------------------
    # 단계 우선순위 0: 검사 설명 완료 후에는 반드시 검사결과 확인으로 진행
    # ------------------------------------------------------------
    # 검사 설명과 환자 참여 확인이 끝난 뒤에는 학생이
    # “검사 진행하겠습니다”, “검사 시행하겠습니다”, “We will conduct the test”처럼
    # 짧게 말해도 중재 수행이나 일반 반응으로 빠지지 않고 바로 검사결과가 제시되어야 한다.
    # 이전 버전에서는 “진행하겠습니다”가 intervention_do_keywords에 먼저 걸려
    # 처방 전 중재 수행 오류 안내로 분류되는 문제가 있었다.
    # 따라서 이 잠금장치를 SBAR/중재 분류보다 앞에 둔다.
    if st.session_state.get("exam_explained", False) and not st.session_state.get("labs_shown", False):
        return "labs"

    # SBAR 상세 보고
    report_action_keywords = [
        "보고", "보고하겠습니다", "sbar", "sbar 형식", "병원 보고 형식",
        "보고 내용", "보고드립니다", "보고 드립니다",
        "노티드립니다", "노티 드립니다", "의사에게 보고", "의료진 보고",
        "의사선생님", "의사 선생님", "처방 부탁", "처방 요청"
    ]
    report_content_keywords = [
        "김심근", "62세", "흉통", "흉통 지속", "불안 호소",
        "nrs", "8점", "30분", "고혈압", "흡연", "가족력",
        "검사 완료", "심전도", "ecg", "ekg", "ekg상 st 상승",
        "st 상승", "트로포닌", "troponin", "ck-mb", "ckmb",
        "ami", "ami 의심", "급성심근경색", "급성심근경색 의심", "심근경색", "stemi"
    ]
    sbar_structure = has_any(text, ["s:", "b:", "a:", "r:", "situation", "background", "assessment", "recommendation", "상황", "배경", "사정", "제안"])
    if (has_any(text, report_action_keywords) and has_any(text, report_content_keywords)) or (sbar_structure and has_any(text, report_content_keywords)):
        return "report_detail"

    # 상호작용 완료 후에는 SBAR 또는 보고 의도가 확인되면 처방이 제시되도록 한다.
    # 체크리스트는 완료되었는데 의사 처방이 보이지 않는 문제를 방지하기 위한 보완 조건이다.
    if st.session_state.interaction_completed and (
        has_any(text, ["sbar", "s:", "b:", "a:", "r:", "보고", "보고드립니다", "보고 드립니다", "노티", "notify", "의사에게"])
        or sbar_structure
    ):
        return "report_detail"

    # 처방 확인 후에는 '처방', '산소', '약물', '투여', '진행' 표현을
    # SBAR 보고 예고가 아니라 중재 설명/중재 수행 단계로 우선 분류한다.
    post_order_intervention_keywords = [
        "처방", "처방에 따라", "처방대로", "산소", "산소요법", "산소 투여", "산소를 투여",
        "약", "약물", "투여", "니트로", "니트로글리세린", "ntg",
        "아스피린", "aspirin", "중재", "시행", "진행", "해도 될까요", "괜찮을까요",
        "불편", "부작용", "증상 있으면", "알려주세요", "말씀해주세요",
        "콜벨", "콜밸", "호출벨", "간호사 부르", "불러주세요",
        "동의해주세요", "동의하시나요", "동의해주시면"
    ]
    if st.session_state.order_shown and has_any(text, post_order_intervention_keywords):
        if st.session_state.intervention_explained:
            return "intervention"
        return "intervention_explanation"

    # 단순 보고 예고
    simple_report_keywords = [
        "보고하겠습니다", "보고 하겠습니다", "보고하도록", "보고할게요", "보고 드릴게요",
        "노티하겠습니다", "노티 하겠습니다", "의사에게 알리", "의사에게 보고",
        "의료진에게 보고", "의사선생님", "의사 선생님",
    ]
    if has_any(text, simple_report_keywords):
        return "report_intro"

    # ------------------------------------------------------------
    # 단계 우선순위 1: 상호작용
    # 검사결과 확인 후, SBAR 보고 전에는 "산소/약물/치료/협조" 표현이
    # 중재 설명이나 중재 수행이 아니라 King의 상호작용 단계
    # (문제 확인·간호목표 공유·목표달성 방법 설명·방법 합의)로 우선 분류된다.
    # ------------------------------------------------------------
    interaction_keywords = [
        "문제", "현재 문제", "가장 힘든", "가장 큰 문제",
        "목표", "공동 목표", "치료 목표", "간호 목표", "goal", "goals", "aim", "objective",
        "통증을 줄", "통증 완화", "통증 감소", "pain", "chest pain",
        "숨쉬기 편", "숨 쉬기 편", "호흡을 편", "호흡곤란 완화",
        "breathing", "shortness of breath", "dyspnea",
        "불안", "불안 완화", "불안 감소", "안정", "anxiety", "anxious",
        "이를 위해", "방법", "다음 조치", "우선 조치",
        "산소", "산소요법", "산소 공급", "산소공급",
        "약물", "약", "약물 치료", "약물 투여",
        "치료", "중재", "처치",
        "협조", "환자 협조", "협조 요청", "협조해 주실 수", "협조해주시겠",
        "진행해도", "진행해도 괜찮", "진행해도 될까요",
        "괜찮을까요", "괜찮으실까요", "동의", "동의하시", "해도 될까요"
    ]
    if (
        st.session_state.labs_shown
        and not st.session_state.interaction_completed
        and has_any(text, interaction_keywords)
    ):
        return "interaction_goal_setting"

    # ------------------------------------------------------------
    # 단계 우선순위 2: 중재 설명
    # SBAR 보고 및 처방 확인 후에는 동일한 "산소/약물/협조" 표현을
    # 교류작용 단계의 중재 설명으로 분류한다.
    # ------------------------------------------------------------
    intervention_explain_keywords = [
        "중재", "중재 필요성", "산소요법", "산소", "o2", "o₂",
        "약", "약물", "약물 투여", "약물 작용",
        "필요한 이유", "니트로", "니트로글리세린", "ntg",
        "혈관확장", "혈관 확장", "혈류공급", "혈류 공급", "산소공급", "산소 공급",
        "아스피린", "aspirin", "아스피린 중재", "플라빅스", "plavix", "클로피도그렐", "혈전 예방",
        "심전도 재확인", "ecg monitoring", "관상동맥조영술", "관상동맥 조영술", "cag", "cag preparation",
        "통증", "통증 감소", "호흡", "숨쉬기", "불편", "어지럽", "부작용",
        "불편하면 말씀", "환자 협조", "이해되도록 설명",
        "콜벨", "콜밸", "호출벨", "간호사 부르", "불러주세요", "말씀해주세요", "알려주세요",
        "불편하면", "이상하면", "동의해주세요", "동의하시나요", "동의해주시면",
        "진행해도", "진행해도 괜찮", "진행해도 될까요", "진행하겠습니다",
        "괜찮을까요", "괜찮으실까요", "협조"
    ]
    intervention_do_keywords = [
        "처방에 따라", "처방대로", "시행하겠습니다", "수행하겠습니다", "진행하겠습니다",
        "이제 진행", "처치하겠습니다", "중재하겠습니다",
        "산소 투여", "산소를 투여", "산소 적용", "산소 연결",
        "산소요법 시행", "산소 요법 시행",
        "비강캐뉼라", "비강 캐뉼라", "ntg 투여", "니트로 투여", "니트로글리세린 투여",
        "아스피린 투여", "플라빅스 투여", "plavix", "모르핀", "morphine", "약물을 투여", "약물 투여", "12-lead", "12유도",
        "심전도 재확인", "ecg re-check", "ekg re-check", "ecg monitoring", "모니터링",
        "cag preparation", "cag 준비", "관상동맥조영술 준비", "관상동맥 조영술 준비"
    ]

    if (
        st.session_state.order_shown
        and not st.session_state.intervention_explained
        and (has_any(text, intervention_explain_keywords) or has_any(text, intervention_do_keywords))
    ):
        return "intervention_explanation"

    # ------------------------------------------------------------
    # 단계 우선순위 3: 중재 수행
    # 실제 처방 기반 중재 수행은 처방 확인(order_shown)과 중재 설명 완료
    # (intervention_explained)가 모두 끝난 뒤에만 인정한다.
    # ------------------------------------------------------------
    if (
        st.session_state.order_shown
        and st.session_state.intervention_explained
        and has_any(text, intervention_do_keywords)
    ):
        return "intervention"

    # 처방 전 중재 수행 시도는 get_response()에서 오류 안내가 가능하도록
    # intervention으로 분류하되, 상호작용 단계가 열려 있는 경우에는 위에서 이미
    # interaction_goal_setting으로 우선 분류된다.
    if (
        not st.session_state.order_shown
        and has_any(text, intervention_do_keywords)
    ):
        return "intervention"

    # ------------------------------------------------------------
    # 단계 역행 방지 잠금장치
    # 이미 다음 단계로 진행한 뒤에는 학생이 이전 단계 표현을 다시 말하더라도
    # 환자 반응이 이전 단계로 되돌아가지 않도록 현재 또는 다음 순서의 단계로 보낸다.
    # 예: 검사결과 확인 후 "급성심근경색이 의심됩니다"라고 말하면
    # 5단계 AMI 판단으로 돌아가지 않고 8단계 상호작용의 문제 확인으로 처리한다.
    # ------------------------------------------------------------
    if st.session_state.get("order_shown", False) and not st.session_state.get("intervention_done", False):
        # 실제 중재 수행은 위의 intervention_do_keywords 조건을 만족할 때만 "intervention"으로 보낸다.
        # 그 외의 모호한 입력은 10단계 중재 설명 맥락으로 유지하여 조기 수행을 방지한다.
        return "intervention_explanation"

    if st.session_state.get("interaction_completed", False) and not st.session_state.get("sbar_reported", False):
        return "report_intro"

    if st.session_state.get("labs_shown", False) and not st.session_state.get("interaction_completed", False):
        return "interaction_goal_setting"

    if st.session_state.get("exam_explained", False) and not st.session_state.get("labs_shown", False):
        return "labs"

    if st.session_state.get("ami_judged", False) and not st.session_state.get("exam_explained", False):
        return "exam_explanation"

    # 심근경색 또는 심장·심혈관 문제 가능성 판단
    # 자연스러운 표현(예: "급성심근경색이 의심됩니다", "심장 문제일 가능성이 있습니다",
    # "It could be a heart problem")도 잡기 위해 보강 함수 사용.
    if is_ami_judgment_statement(text):
        return "ami_judgment"

    # 병력·위험요인 확인: 활력징후보다 먼저 둔다.
    family_history_keywords = [
        "가족력", "가족 중", "심장질환 가족", "심질환 가족",
        "아버지", "어머니", "부친", "모친"
    ]
    if has_any(text, family_history_keywords):
        return "family_history"

    history_keywords = [
        "과거력", "병력", "과거 병력", "조심해야 할 병력", "기저질환",
        "고혈압", "혈압약", "혈압 약", "고혈압 약",
        "당뇨", "고지혈증", "심장질환", "심질환",
        "진단받", "앓고", "질환 있으",
        "복용약", "복용약물", "현재 복용 약물", "약 드시", "약 먹", "복용중인",
        "복용 중인", "최근 복용", "항응고제", "항응고", "항혈소판제", "항혈소판",
        "와파린", "헤파린", "아스피린", "플라빅스", "클로피도그렐", "피 묽게", "피를 묽게",
        "출혈성 질환", "출혈 질환", "출혈질환", "출혈", "피가 잘", "지혈", "혈우병",
        "담배", "흡연", "음주", "술", "알레르기",
        "식습관", "생활습관", "운동", "운동 부족", "위험요인"
    ]
    if has_any(text, history_keywords):
        return "history"

    # 검사 필요성 설명: 누적 인식
    # 검사 설명이 아직 완료되지 않은 상태에서는 'troponin', '심장근육 손상' 같은 표현이
    # 검사결과 확인(labs)이 아니라 혈액검사 설명(exam_explanation)으로 먼저 분류되도록 한다.
    exam_keywords = [
        "검사 이유", "검사 필요성", "왜 검사", "왜 해야",
        "심전도", "ecg", "ekg", "12유도", "12-lead", "electrocardiogram", "electrocardiography",
        "혈액검사", "혈액 검사", "피검사", "채혈", "심근효소", "myocardial enzyme", "cardiac enzyme", "blood test", "blood work",
        "검사", "정확한 상태 파악", "정확한 확인", "상태 확인", "정밀한 진단", "accurate confirmation",
        "관련 수치", "전기적 변화", "심장근육 손상", "심근 손상", "heart muscle damage",
        "트로포닌", "troponin", "ck-mb", "ckmb",
        "알기 쉽게", "알아듣기 쉽게", "이해하기 쉽게",
        "납득할 수 있도록", "협조", "협조 요청", "불안 완화", "cooperate", "consent", "proceed"
    ]
    if not st.session_state.exam_explained and has_any(text, exam_keywords):
        return "exam_explanation"

    # 검사결과 확인/임상 판단: 검사 설명이 완료된 이후에만 검사결과 확인으로 분류한다.
    labs_keywords = [
        "검사결과", "검사 결과", "검사수치", "검사 수치", "검사시행", "검사 시행",
        "검사 진행", "검사를 진행", "검사하겠습니다", "검사 하겠습니다", "검사 진행하겠습니다",
        "검사 결과 확인", "검사결과 확인", "검사 결과를 확인", "검사결과를 확인",
        "검사 결과 확인하겠습니다", "검사 결과를 확인하겠습니다", "검사결과 확인하겠습니다", "검사결과를 확인하겠습니다",
        "결과 확인", "결과를 확인", "결과 해석", "결과 토대로",
        "conduct the test", "conduct a test", "conduct an inspection", "conduct inspection", "we will conduct the test", "we will conduct an inspection", "proceed with the test",
        "proceed with an inspection", "proceed with inspection", "perform the test", "run the test", "check the results", "check the test results",
        "i will check the results", "i will check the test results", "we will check the test results",
        "심전도 결과", "혈액검사 결과", "lab",
        "환자 상태", "상태 판단", "정상 수치", "정상범위",
        "비정상 수치", "이상 수치", "의미있는 자료", "의미 있는 자료",
        "st 상승", "st분절", "st 분절", "troponin", "트로포닌",
        "ck-mb", "ckmb", "ami", "ami 의심", "급성심근경색",
        "심근경색", "stemi", "유추되는 질환명", "감별진단",
        "다른 질병", "다음 조치", "우선 조치", "처치 필요"
    ]
    if st.session_state.exam_explained and (has_any(text, labs_keywords) or is_labs_transition_expression(text)):
        return "labs"

    # 상호작용/중재 설명/중재 수행 분류는 위 단계 우선순위 블록에서 처리한다.

    # 활력징후 확인
    vitals_keywords = [
        "활력징후", "바이탈", "현재 바이탈", "정상 바이탈",
        "v/s", "vs", "혈압", "bp", "맥박", "pr",
        "호흡수", "rr", "산소포화도", "spo2", "saturation", "세츄", "체온", "bt",
        "정상 수치", "정상범위", "이상 수치", "비정상 수치", "검사수치", "객관적 자료"
    ]
    vitals_action_keywords = [
        "확인", "측정", "측정해", "체크", "알려줘", "보여줘",
        "수치", "현재", "몇", "결과", "정상", "비정상", "이상"
    ]
    history_exclusion_keywords = [
        "고혈압", "혈압약", "혈압 약", "고혈압 진단",
        "고혈압 있으", "고혈압 앓", "혈압약 복용"
    ]
    if (
        has_any(text, vitals_keywords)
        and has_any(text, vitals_action_keywords)
        and not has_any(text, history_exclusion_keywords)
    ):
        return "vitals"

    # 통증 및 증상 사정
    pain_keywords = [
        "통증", "흉통", "가슴 답답", "가슴이 답답", "가슴", "쥐어짜는", "꽉 쥐어짜는",
        "어디", "어디서부터", "위치", "어떻게", "양상", "느낌", "언제", "언제부터",
        "시작", "지속", "얼마나 지속", "통증 강도", "통증점수", "통증 점수",
        "몇 점", "1-10", "nrs", "통증척도", "방사통", "방사", "퍼지",
        "턱", "왼쪽 어깨", "어깨", "등", "등 통증", "등으로", "등쪽", "뒤쪽", "방사통", "동반 증상", "다른 증상",
        "악화요인", "악화 요인", "완화요인", "완화 요인", "악화", "완화",
        "움직이면", "움직일 때", "움직", "가만히", "쉬면", "쉬어도", "안정", "나아지", "심해지",
        "숨참", "숨 참", "호흡곤란", "숨이", "숨", "식은땀",
        "불안 정도", "불안", "두려", "무섭", "아프", "답답"
    ]
    if has_any(text, pain_keywords):
        return "pain_assessment"

    therapeutic_keywords = [
        "괜찮", "도와", "안심", "안심 표현", "안정", "안정시키는 말",
        "걱정하지", "걱정하지 않으셔도 됩니다", "걱정", "옆에",
        "진정", "함께", "공감", "위로", "정신적 지지",
        "계속 살피고 있습니다", "옆에 있겠습니다"
    ]
    if has_any(text, therapeutic_keywords):
        return "therapeutic"

    return "general"




def get_focused_history_risk_response(text: str) -> str:
    """병력·위험요인 사정 단계에서 학생이 물은 항목에만 초점을 맞춰 짧게 응답한다.

    OpenAI 자연화 응답을 사용하면 가족력 질문에도 현재 흉통·호흡곤란·검사 요청이 덧붙어
    학생이 질문의 초점을 파악하기 어려웠다. 따라서 병력·위험요인 단계는 고정값 기반으로
    질문한 항목에만 답한다.
    """
    response_parts: List[str] = []

    hypertension_keywords = ["고혈압", "혈압", "기저질환", "과거력", "병력", "진단", "질환"]
    medication_keywords = ["약", "약물", "복용", "복용약", "혈압약", "드시", "먹고", "먹는"]
    family_keywords = ["가족력", "가족", "아버지", "부친", "어머니", "모친", "심장마비", "심장질환"]
    smoking_keywords = ["담배", "흡연", "흡연력", "smoking", "smoke"]
    anticoagulant_keywords = ["항응고", "항응고제", "항혈소판", "항혈소판제", "와파린", "헤파린", "아스피린", "플라빅스", "피 묽게", "피를 묽게"]
    bleeding_keywords = ["출혈", "출혈성", "출혈 질환", "출혈질환", "피가 잘", "지혈", "혈우병"]
    allergy_keywords = ["알레르기", "알러지", "allergy"]
    diabetes_keywords = ["당뇨", "diabetes"]
    hyperlipidemia_keywords = ["고지혈", "고지혈증", "이상지질", "콜레스테롤"]
    alcohol_keywords = ["음주", "술", "alcohol"]
    diet_keywords = ["식습관", "식사", "식이", "생활습관"]
    exercise_keywords = ["운동"]

    # 여러 항목을 한 번에 물으면, 물은 항목만 순서대로 답한다.
    if has_any(text, hypertension_keywords):
        response_parts.append("고혈압이 있고, 6년 전에 진단받았어요.")
    if has_any(text, medication_keywords):
        response_parts.append("혈압약은 먹고 있는데 약 이름은 잘 몰라요.")
    if has_any(text, family_keywords):
        response_parts.append("아버지가 심장마비로 돌아가셨어요.")
    if has_any(text, smoking_keywords):
        response_parts.append("담배는 20년 전부터 하루 한 갑 정도 피웠어요.")
    if has_any(text, anticoagulant_keywords):
        response_parts.append("최근 항응고제나 항혈소판제는 복용하지 않았어요.")
    if has_any(text, bleeding_keywords):
        response_parts.append("출혈성 질환은 없어요.")
    if has_any(text, allergy_keywords):
        response_parts.append("알레르기는 없어요.")
    if has_any(text, diabetes_keywords):
        response_parts.append("당뇨 진단 여부는 잘 모르겠어요.")
    if has_any(text, hyperlipidemia_keywords):
        response_parts.append("고지혈증 진단 여부는 잘 모르겠어요.")
    if has_any(text, alcohol_keywords):
        response_parts.append("음주는 특별히 말씀드릴 만한 건 잘 모르겠어요.")
    if has_any(text, diet_keywords):
        response_parts.append("식사는 불규칙한 편이에요.")
    if has_any(text, exercise_keywords):
        response_parts.append("운동은 거의 하지 않아요.")

    if response_parts:
        # 중복 문장 제거 후 반환
        unique_parts: List[str] = []
        for part in response_parts:
            if part not in unique_parts:
                unique_parts.append(part)
        return " ".join(unique_parts)

    # 질문이 넓은 병력 질문인 경우에도 현재 증상이나 검사 요구를 덧붙이지 않는다.
    return "고혈압이 있고 혈압약은 먹고 있는데 약 이름은 잘 몰라요. 아버지가 심장마비로 돌아가셨어요."


def get_focused_pain_assessment_response(text: str) -> str:
    """통증 사정 단계에서 학생이 물은 항목에만 초점을 맞춰 짧게 응답한다.

    기존 OpenAI 자연화 응답은 환자의 불안 표현과 추가 질문을 덧붙이면서
    "언제부터 아팠나요?" 같은 단일 질문에도 "큰일 난 건가요? 빨리 검사해 주세요"처럼
    불필요한 문장이 포함될 수 있었다. 파일럿 테스트에서 학생들이 답변의 초점을
    파악하기 어렵다는 피드백이 있어, 통증 사정 단계는 고정값 기반의 직접 응답으로 처리한다.
    """
    response_parts: List[str] = []

    location_keywords = ["어디", "위치", "부위", "어디가", "어디서부터"]
    quality_keywords = ["어떻게", "양상", "느낌", "쥐어짜", "압박", "조이", "답답", "찌르", "저리"]
    onset_keywords = ["언제", "언제부터", "시작", "시작했", "지속", "얼마나", "몇 분", "몇시간", "몇 시간"]
    score_keywords = ["몇 점", "몇점", "nrs", "점수", "강도", "1-10", "0점", "10점", "통증척도", "통증 척도"]
    radiation_keywords = ["방사", "퍼지", "퍼지는", "턱", "어깨", "왼쪽 어깨", "왼팔", "팔", "등", "등 통증", "등으로", "등쪽", "뒤쪽"]
    associated_keywords = ["숨", "숨참", "숨차", "숨 차", "호흡곤란", "식은땀", "식은 땀", "동반", "다른 증상", "불안", "무서"]
    factor_keywords = ["악화요인", "악화 요인", "완화요인", "완화 요인", "악화", "완화", "움직이면", "움직일 때", "움직", "가만히", "쉬면", "쉬어도", "안정", "나아지", "심해지"]

    if has_any(text, location_keywords):
        response_parts.append("가슴 한가운데가 아파요.")
    if has_any(text, quality_keywords):
        response_parts.append("누가 꽉 쥐어짜는 듯한 압박감이에요.")
    if has_any(text, onset_keywords):
        response_parts.append("30분 전 운전 중에 갑자기 시작됐어요.")
    if has_any(text, score_keywords):
        response_parts.append("통증은 8점 정도예요.")
    if has_any(text, radiation_keywords):
        response_parts.append("턱, 왼쪽 어깨, 등까지 퍼져요.")
    if has_any(text, associated_keywords):
        response_parts.append("숨이 차고 식은땀이 나며 많이 불안해요.")
    if has_any(text, factor_keywords):
        response_parts.append("가만히 있어도 계속 아프고, 쉬어도 뚜렷하게 나아지지 않아요.")

    if response_parts:
        return " ".join(response_parts)

    # 질문이 모호하지만 통증 사정 단계로 분류된 경우에는 핵심 증상만 짧게 말한다.
    return "가슴 한가운데가 꽉 조이듯 아프고, 통증은 8점 정도예요."


# ------------------------------------------------------------
# 11. 응답 생성
# ------------------------------------------------------------
def get_response(user_text: str) -> List[Dict[str, str]]:
    category = classify_input(user_text)
    st.session_state._current_response_step_label = get_step_label_for_category(category)
    responses: List[Dict[str, str]] = []

    if category == "intro":
        st.session_state.intro_done = True
        mark_checklist("1. 지각: 초기 접촉 및 주호소 확인")
        # 환자 확인은 체크리스트 완료 조건으로만 반영하고,
        # 화면에는 별도의 [시스템 | 환자 확인] 메시지를 표시하지 않는다.
        responses.append(patient_message(
            f"네… {PATIENT_INFO['name']}입니다. 등록번호는 {PATIENT_INFO['registration_number']}이고, 팔찌도 맞아요. 가슴 한가운데가 너무 꽉 조여요… 숨도 차고 식은땀이 나요. 저 이러다 큰일 나는 거 아니죠?"
        ))

    elif category == "pain_assessment":
        # 안전장치: 중재 후에는 통증 관련 입력이 초기 사정으로 되돌아가지 않고 재사정으로 처리된다.
        if st.session_state.get("intervention_done", False) and not st.session_state.get("reassessment_done", False):
            updates = update_reassessment_state(user_text)
            responses.append(patient_message(get_reassessment_patient_response_for_current_state(updates)))
            return responses

        st.session_state.pain_symptom_done = True
        mark_checklist("2. 지각: 통증 및 동반 증상 사정")

        # 통증 사정 단계는 질문한 항목에만 답하도록 고정 응답을 사용한다.
        # 예: "언제부터 아팠나요?" → "30분 전 운전 중에 갑자기 시작됐어요."
        # 불필요한 "큰일 난 건가요/빨리 검사해 주세요" 표현은 제외한다.
        responses.append(patient_message(get_focused_pain_assessment_response(user_text)))

    elif category == "vitals":
        st.session_state.vitals_shown = True
        st.session_state.vitals_done = True
        mark_checklist("3. 지각: 활력징후 확인")
        responses.append(vital_message(
            "초기 활력징후\n"
            f"- BP: {VITAL_SIGNS['BP']}\n"
            f"- HR: {VITAL_SIGNS['HR']}\n"
            f"- RR: {VITAL_SIGNS['RR']}\n"
            f"- SpO₂: {VITAL_SIGNS['SpO2']}\n"
            f"- BT: {VITAL_SIGNS['BT']}"
        ))
        responses.append(patient_message("혈압이랑 맥박이 많이 높은 거예요…? 가슴도 계속 답답한데, 저 지금 위험한 상태인가요?"))

    elif category == "family_history":
        st.session_state.history_risk_done = True
        mark_checklist("4. 지각: 병력 및 위험요인 사정")
        # 가족력 질문에는 현재 증상이나 검사 요청을 덧붙이지 않고, 질문한 내용에만 답한다.
        responses.append(patient_message(get_focused_history_risk_response(user_text)))

    elif category == "history":
        st.session_state.history_risk_done = True
        mark_checklist("4. 지각: 병력 및 위험요인 사정")
        # 병력·위험요인 질문에는 질문한 항목만 고정값으로 답한다.
        # OpenAI 자연화 응답을 사용하지 않아 불필요한 흉통/호흡곤란/검사 요청 문장이 덧붙지 않는다.
        responses.append(patient_message(get_focused_history_risk_response(user_text)))

    elif category == "ami_judgment":
        st.session_state.ami_judged = True
        mark_checklist("5. 판단: 심혈관질환 의심 상황 판단 및 검사 필요성 인식")
        responses.append(patient_message(
            "심장 문제일 수도 있다는 건가요…? 너무 무서워요. 그래도 정확히 확인하려면 심전도랑 피검사를 해야 한다는 말씀이시죠?"
        ))
        responses.append(system_message(
            "심근경색 또는 심혈관질환 가능성 인식이 확인되었습니다. 심전도와 혈액검사의 필요성을 환자에게 설명하고 협조를 구하세요."
        ))

    elif category == "exam_explanation":
        updates = update_exam_explanation_state(user_text)

        if st.session_state.exam_explained:
            st.session_state.exam_error_count = 0
            responses.append(patient_message(
                "아… 심전도는 심장 상태를 보고, 피검사는 심장근육 손상 여부를 확인하는 거군요. "
                "무섭긴 하지만 설명 들었으니까 검사 진행해 주세요…"
            ))

            # 학생의 현재 입력 자체가 검사 시행/진행/결과 확인 의도라면
            # 다음 입력을 기다리지 않고 바로 Step 7 검사결과를 제시한다.
            # 예: "검사 진행하겠습니다", "검사 결과를 확인하겠습니다",
            # "We will conduct an inspection", "execution of test", "progress of test".
            if is_labs_transition_expression(user_text) and not st.session_state.get("labs_shown", False):
                st.session_state.labs_shown = True
                mark_checklist("7. 상호작용: 검사결과 기반 문제 구체화")
                responses.append(lab_message(
                    "검사결과\n"
                    f"- ECG: {LAB_RESULTS['ECG']}\n"
                    f"- Troponin I: {LAB_RESULTS['Troponin I']} (정상수치 {LAB_NORMAL_RANGES['Troponin I']})\n"
                    f"- CK-MB: {LAB_RESULTS['CK-MB']} (정상수치 {LAB_NORMAL_RANGES['CK-MB']})"
                ))
                responses.append(patient_message("검사 결과가 안 좋은 건가요…? 아직 가슴이 답답하고 숨도 좀 차서 너무 걱정돼요."))
            else:
                responses.append(system_message("검사 설명 및 이해와 참여 확인이 완료되었습니다. 검사결과를 확인할 수 있습니다."))
        else:
            if updates:
                st.session_state.exam_error_count = 0
            else:
                st.session_state.exam_error_count = st.session_state.get("exam_error_count", 0) + 1

            responses.append(patient_message(get_exam_patient_response_for_current_state(updates)))

            if st.session_state.exam_error_count >= 2:
                responses.append(hint_message(get_exam_hint_text()))

    elif category == "labs":
        if not st.session_state.exam_explained:
            responses.append(patient_message(
                "선생님… 무슨 검사를 하는 거예요? 왜 해야 하는지 먼저 설명해주시면 좋겠어요. 너무 불안해서요…"
            ))
            responses.append(system_message("검사결과는 학생이 심전도·혈액검사 필요성을 설명하고 환자의 협조를 얻은 후 확인할 수 있습니다."))
        else:
            st.session_state.labs_shown = True
            mark_checklist("7. 상호작용: 검사결과 기반 문제 구체화")
            responses.append(lab_message(
                "검사결과\n"
                f"- ECG: {LAB_RESULTS['ECG']}\n"
                f"- Troponin I: {LAB_RESULTS['Troponin I']} (정상수치 {LAB_NORMAL_RANGES['Troponin I']})\n"
                f"- CK-MB: {LAB_RESULTS['CK-MB']} (정상수치 {LAB_NORMAL_RANGES['CK-MB']})"
            ))
            responses.append(patient_message("검사 결과가 안 좋은 건가요…? 아직 가슴이 답답하고 숨도 좀 차서 너무 걱정돼요."))

    elif category == "interaction_goal_setting":
        if not st.session_state.labs_shown:
            responses.append(system_message(
                "상호작용 단계는 검사결과 확인 후 진행합니다. 먼저 검사결과를 확인하세요."
            ))
        else:
            updates = update_interaction_state(user_text)

            if st.session_state.interaction_completed:
                st.session_state.interaction_error_count = 0
                responses.append(patient_message(
                    "네… 제 문제는 가슴 통증이 등까지 퍼지는 것과 숨찬 증상이고, 목표는 통증을 줄이고 숨쉬기 편해지는 거군요. "
                    "산소와 약물치료, 심전도 재확인이 필요하고, 막힌 혈관이 있는지 확인해 필요한 치료를 빠르게 진행하기 위해 관상동맥조영술 준비가 필요할 수 있다는 것도 이해했어요… 말씀하신 방법에 협조할게요."
                ))
                responses.append(system_message(
                    "상호작용 단계가 완료되었습니다. 다음 단계로 SBAR 보고를 진행하세요."
                ))
            else:
                if updates:
                    st.session_state.interaction_error_count = 0
                else:
                    st.session_state.interaction_error_count = st.session_state.get("interaction_error_count", 0) + 1

                responses.append(patient_message(get_interaction_patient_response_for_current_state(updates)))

                if st.session_state.interaction_error_count >= 2:
                    responses.append(hint_message(get_interaction_hint_text()))

    elif category == "report_intro":
        if not st.session_state.interaction_completed:
            responses.append(system_message(
                "SBAR 보고 전, 환자와 현재 문제, 간호목표, 목표달성 방법을 먼저 공유하고 환자의 이해와 참여 의사를 확인하세요."
            ))
        else:
            responses.append(patient_message("네… 의사 선생님께 빨리 말씀드려 주세요. 가슴이 계속 답답해서 너무 무서워요…"))
            responses.append(system_message("SBAR 형식으로 환자 상태, 배경, 사정결과, 제안을 포함하여 보고하면 처방이 제시됩니다."))

    elif category == "report_detail":
        if not st.session_state.interaction_completed:
            responses.append(system_message(
                "SBAR 보고 전 상호작용 단계를 완료하세요: 문제 확인, 간호목표 공유, 방법 설명, 환자의 이해와 참여 확인이 필요합니다."
            ))
        else:
            st.session_state.sbar_reported = True
            st.session_state.order_shown = True
            mark_checklist("9. 교류작용: SBAR 보고 및 처방 확인")

            order_text = (
                "의사 처방\n"
                + "\n".join([f"{idx}. {order}" for idx, order in enumerate(DOCTOR_ORDER, start=1)])
            )
            responses.append(order_message(order_text))

    elif category == "intervention_explanation":
        if not st.session_state.order_shown:
            responses.append(system_message("중재 설명 전 SBAR 보고를 완료하고 의사 처방을 먼저 확인해야 합니다."))
        else:
            updates = update_intervention_explanation_state(user_text)

            if st.session_state.intervention_explained:
                st.session_state.intervention_error_count = 0
                st.session_state.cooperation_formed = True
                mark_checklist("10. 교류작용: 중재 설명 및 중재 수행")
                responses.append(patient_message(
                    "네… 설명 들으니 조금 안심돼요. 불편하거나 어지러우면 바로 말씀드릴게요… 진행해 주세요."
                ))
            else:
                # 중재 설명 힌트 제시 원칙(v26)
                # - 힌트는 “단계가 아직 미완료”라는 이유만으로 바로 제시하지 않는다.
                # - 학생이 산소 설명, 약물 설명, 이상반응 안내처럼 새 핵심 항목을 하나라도 채우면
                #   정상적으로 진행 중인 것으로 보고 힌트를 보류하며 카운트를 0으로 초기화한다.
                # - 힌트는 같은 단계에서 새로 인정되는 핵심 항목 없이 2회 연속 막힌 경우에만 제시한다.
                #   예: 환자가 “약은 어떤 약이고 왜 필요한가요?”라고 물었는데 학생이 계속 산소만 반복 설명하는 경우.
                previous_error_count = st.session_state.get("intervention_error_count", 0)

                responses.append(patient_message(get_intervention_patient_response_for_current_state(updates)))

                if updates:
                    # 새 핵심 항목이 인식되었으면 학습자가 진행 중이므로 힌트를 띄우지 않는다.
                    st.session_state.intervention_error_count = 0
                else:
                    current_error_count = previous_error_count + 1
                    if current_error_count >= 2:
                        responses.append(hint_message(get_intervention_hint_text()))
                        # 힌트가 매 입력마다 반복되지 않도록 제시 후 초기화한다.
                        st.session_state.intervention_error_count = 0
                    else:
                        st.session_state.intervention_error_count = current_error_count
    elif category == "intervention":
        if not st.session_state.order_shown:
            responses.append(system_message("아직 의사 처방이 제시되지 않았습니다. SBAR 보고 후 처방을 확인하세요."))
        elif not st.session_state.intervention_explained:
            responses.append(patient_message(
                "선생님… 산소와 약을 바로 하기 전에 왜 필요한지, 불편하면 어떻게 해야 하는지 설명해 주세요. "
                "설명 듣고 진행해도 되는지 말씀드릴게요…"
            ))
            responses.append(system_message("중재 수행 전 산소요법과 약물의 목적, 이상반응/불편감 안내, 환자의 이해와 참여 확인이 필요합니다."))
        else:
            st.session_state.intervention_done = True
            st.session_state.current_phase = "post_intervention_reassessment"
            st.session_state.cooperation_formed = True
            mark_checklist("10. 교류작용: 중재 설명 및 중재 수행")
            responses.append(order_message(
                "처방 기반 중재 수행\n"
                + "\n".join([f"- {order}" for order in DOCTOR_ORDER])
            ))
            responses.append(patient_message("네… 설명 들었으니까 진행해주세요. 아직 무섭긴 한데, 선생님 말씀 믿고 해볼게요…"))
            # 중재 후 활력징후 재측정값과 5분 후 재사정 안내는 환자 반응 다음에 하나의 화면으로 제시한다.
            # 이 값은 화면 안내용이며 11단계 완료 조건에는 포함하지 않는다.
            responses.append(post_intervention_vital_response())

    elif category == "post_intervention_vitals":
        # 중재 후 활력징후 요청은 초기 활력징후나 초기 환자 반응으로 되돌아가지 않고
        # 중재 후 고정 활력징후만 제시한다.
        responses.append(post_intervention_vital_response())

    elif category == "reassessment":
        # 재사정 단계는 학생이 질문한 항목에 대해서만 환자가 답하도록 한다.
        # 중재 후 활력징후와 5분 후 재사정 안내는 중재 수행 직후 이미 제시되며,
        # 활력징후 재측정은 11단계 완료 조건이나 세부 체크 항목에 포함하지 않는다.
        updates = update_reassessment_state(user_text)

        responses.append(patient_message(get_reassessment_patient_response_for_current_state(updates)))

        if reassessment_all_checked():
            st.session_state.reassessment_done = True
            st.session_state.goal_achieved = True
            st.session_state.current_phase = "debriefing"
            mark_checklist("11. 목표달성: 중재 후 재사정 및 목표달성 확인")

            # 자동 화면 이동을 막기 위해 디브리핑 영역으로 강제 스크롤하지 않는다.
            st.session_state.ended = True
            responses.append(completion_message(
                "중재 후 통증 완화 여부, 호흡곤란 감소 여부, 불안 감소 여부 확인과 목표달성 확인이 완료되었습니다. "
                "시뮬레이션이 종료되었습니다. 아래 디브리핑 버튼을 눌러 "
                "환자 사정, 판단, 검사 및 중재 설명, SBAR 보고, 중재 수행, 재사정과 목표달성 확인 과정을 성찰해 주세요."
            ))
        else:
            st.session_state.reassessment_done = False
            st.session_state.goal_achieved = False
            responses.append(system_message(
                "11단계 완료 조건: 중재 후 통증 완화, 호흡곤란 감소, 불안 감소 3가지를 모두 확인해야 목표달성 확인이 완료됩니다."
            ))

    elif category == "closing_therapeutic":
        responses.append(patient_message("네… 다시 아프거나 숨이 차면 바로 말씀드릴게요. 옆에서 봐주시니까 조금 안심돼요…"))

    elif category == "therapeutic":
        responses.append(patient_message("그렇게 말씀해주시니까 조금은 안심돼요… 그래도 가슴이 계속 답답해서 아직 무서워요."))

    else:
        # 시뮬레이션 중에는 정답 예시나 학습 안내를 보여주지 않고,
        # 현재 단계에 맞춰 환자가 자연스럽게 되묻도록 한다.
        if st.session_state.ami_judged and not st.session_state.exam_explained:
            st.session_state.exam_error_count = st.session_state.get("exam_error_count", 0) + 1
            responses.append(patient_message(get_exam_patient_response_for_current_state([])))
            if st.session_state.exam_error_count >= 2:
                responses.append(hint_message(get_exam_hint_text()))
        elif st.session_state.labs_shown and not st.session_state.interaction_completed:
            st.session_state.interaction_error_count = st.session_state.get("interaction_error_count", 0) + 1
            responses.append(patient_message(get_interaction_patient_response_for_current_state([])))
            if st.session_state.interaction_error_count >= 2:
                responses.append(hint_message(get_interaction_hint_text()))
        elif st.session_state.order_shown and not st.session_state.intervention_explained:
            current_error_count = st.session_state.get("intervention_error_count", 0) + 1
            responses.append(patient_message(get_intervention_patient_response_for_current_state([])))
            if current_error_count >= 2:
                responses.append(hint_message(get_intervention_hint_text()))
                st.session_state.intervention_error_count = 0
            else:
                st.session_state.intervention_error_count = current_error_count
        else:
            responses.append(patient_message(get_unclear_patient_response()))

    return responses


# ------------------------------------------------------------
# 12. 세션 초기화 및 사이드바
# ------------------------------------------------------------
init_state()

st.sidebar.markdown("---")
render_progress_indicator()
st.sidebar.markdown("---")

st.sidebar.header("📋 진행 상태")
st.sidebar.caption("'진행상태 보기'를 클릭하면 1단계부터 12단계까지 전체 흐름과 완료 여부를 확인할 수 있습니다.")

with st.sidebar.expander("📋 진행상태 보기: 1단계~12단계", expanded=False):
    st.markdown(
        """
        **진행상태 안내**  
        - 모든 항목을 한 번에 완벽하게 작성해야 다음 단계로 넘어가는 것은 아닙니다.  
        - 학생의 질문과 설명을 누적 인식하여, 단계별 핵심 수행 내용이 충족되면 완료로 표시됩니다.  
        - 단, 검사결과 확인, SBAR 보고, 의사 처방 확인, 중재 수행, 디브리핑은 정해진 순서에 따라 진행됩니다.
        """
    )
    st.markdown("---")
    for key, value in st.session_state.checklist.items():
        desc, criteria = STEP_HELP.get(key, ("단계 설명이 없습니다.", "완료 기준이 설정되지 않았습니다."))
        st.markdown(f"**{'✅' if value else '⬜'} {key}**")
        st.write(f"- 해야 할 일: {desc}")
        st.write(f"- 완료 기준: {criteria}")
        st.markdown("")

st.sidebar.markdown("---")
st.sidebar.subheader("🔎 세부 진행 상태")

with st.sidebar.expander("검사 설명 세부 항목", expanded=False):
    st.write(f"{'✅' if st.session_state.ecg_explained else '⬜'} 심전도 검사 설명")
    st.write(f"{'✅' if st.session_state.blood_test_explained else '⬜'} 혈액검사 설명")
    st.write(f"{'✅' if st.session_state.exam_cooperation_requested else '⬜'} 검사 참여 확인")

with st.sidebar.expander("상호작용 세부 항목", expanded=False):
    st.write(f"{'✅' if st.session_state.problem_identified else '⬜'} 환자 문제 확인")
    st.write(f"{'✅' if st.session_state.goal_set else '⬜'} 간호목표 공유")
    st.write(f"{'✅' if st.session_state.means_explained else '⬜'} 목표달성 방법 설명: 산소요법, 약물치료, 심전도 재확인, 관상동맥조영술 준비 가능성")
    st.write(f"{'✅' if st.session_state.agreement_obtained else '⬜'} 환자의 이해와 참여 확인")

with st.sidebar.expander("중재 설명 세부 항목", expanded=False):
    st.write(f"{'✅' if st.session_state.oxygen_explained else '⬜'} 산소요법 설명")
    st.write(f"{'✅' if st.session_state.medication_explained else '⬜'} 약물투여 설명")
    st.write(f"{'✅' if st.session_state.intervention_purpose_explained else '⬜'} 중재 목적 설명")
    st.write(f"{'✅' if st.session_state.side_effect_guidance_given else '⬜'} 이상반응/불편감 안내")
    st.write(f"{'✅' if st.session_state.intervention_cooperation_requested else '⬜'} 중재 참여 확인")

with st.sidebar.expander("재사정 세부 항목", expanded=False):
    st.write(f"{'✅' if st.session_state.pain_relief_checked else '⬜'} 통증 완화 확인")
    st.write(f"{'✅' if st.session_state.breathing_relief_checked else '⬜'} 호흡곤란 감소 확인")
    st.write(f"{'✅' if st.session_state.anxiety_relief_checked else '⬜'} 불안 감소 확인")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 목표 달성 지표")
st.sidebar.write(f"{'✅' if st.session_state.cooperation_formed else '⬜'} 환자의 이해와 참여 확인")
st.sidebar.write(f"{'✅' if st.session_state.intervention_done else '⬜'} 처방 기반 중재 수행")
st.sidebar.write(f"{'✅' if reassessment_symptoms_all_checked() else '⬜'} 통증·호흡곤란·불안 완화 확인")

# ------------------------------------------------------------
# 13. 시작 / 초기화 버튼
# ------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("▶ 프로그램 시작"):
        reset_simulation()
        st.session_state.started = True
        st.session_state.messages.append(safe_message(patient_message(
            "허억… 선생님… 가슴이 너무 꽉 조여요. 숨도 차고 식은땀이 나요… 저 이러다 죽는 거 아니죠?"
        )))
        st.rerun()

with col2:
    if st.button("🔄 처음부터 다시 시작"):
        reset_simulation()
        st.rerun()

# ------------------------------------------------------------
# 14. 시뮬레이션 대화 화면
# ------------------------------------------------------------
if st.session_state.started:
    st.subheader("💬 시뮬레이션 대화")
    st.caption("챗봇 환자, 학생간호사, 시스템 임상자료, 완료 안내가 색상과 라벨로 구분됩니다.")

    # 이전 버전에서 저장된 HTML/CSS 조각이 화면에 노출되지 않도록 렌더링 전 메시지 기록을 정리한다.
    st.session_state.messages = [sanitize_message_for_display(m) for m in st.session_state.messages]

    for msg in st.session_state.messages:
        render_message(msg)

    # 보완: SBAR 보고 후 order_shown=True인데 의사 처방 카드가 메시지 목록에 없으면 화면에 표시
    # 이전 버전의 [시스템] 처방 메시지가 숨겨지는 문제를 방지한다.
    if st.session_state.get("order_shown", False):
        has_order_card = any(
            ("[의사 처방]" in m.get("content", "")) or ("의사 처방" in m.get("content", ""))
            for m in st.session_state.messages
        )
        if not has_order_card:
            render_message(order_message(
                "의사 처방\n"
                + "\n".join([f"{idx}. {order}" for idx, order in enumerate(DOCTOR_ORDER, start=1)])
            ))

if st.session_state.started and not st.session_state.ended:
    # SBAR 보고는 환자 대화창과 분리하여 전화 보고창에서 수행하도록 구성
    sbar_ready = st.session_state.interaction_completed and not st.session_state.sbar_reported

    if st.session_state.interaction_completed and not st.session_state.sbar_reported:
        st.markdown("---")
        st.markdown("### ☎️ SBAR 보고")
        st.caption("SBAR 보고는 환자 대화와 구분하여 전화 보고창에서 작성합니다.")

        col_call, col_hint = st.columns([1, 2])
        with col_call:
            if st.button("☎️ SBAR 보고창 열기", use_container_width=True):
                st.session_state.show_sbar_window = True
                st.rerun()
        with col_hint:
            st.info("상호작용 단계가 완료되었습니다. 의사에게 SBAR로 보고하면 처방이 제시됩니다.")

    elif not st.session_state.interaction_completed and not st.session_state.sbar_reported:
        st.caption("☎️ SBAR 보고창은 검사결과 확인 후 환자 문제·목표·방법 공유가 완료되면 활성화됩니다.")

    if st.session_state.get("show_sbar_window", False):
        render_sbar_phone_window()

    user_input = st.chat_input("환자에게 질문하거나 간호수행 내용을 입력하세요.")
    if user_input:
        # 화면에 HTML/CSS 코드가 그대로 보이지 않도록 입력 저장 전에 대화문만 정리한다.
        cleaned_user_input = clean_dialogue_text(user_input)
        st.session_state.messages.append(safe_message({"role": "user", "content": cleaned_user_input}))
        for answer in get_response(cleaned_user_input):
            st.session_state.messages.append(safe_message(answer))
        st.rerun()

# ------------------------------------------------------------
# 15. 디브리핑
# ------------------------------------------------------------
if st.session_state.started:
    st.markdown('<div id="debriefing-section"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🧠 디브리핑")

    if not st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        ready_for_debriefing = st.session_state.reassessment_done and st.session_state.goal_achieved
        if not ready_for_debriefing:
            st.info("중재 후 재사정과 목표달성 확인까지 진행한 후 디브리핑을 시작하는 것을 권장합니다.")
        else:
            st.success("프로그램이 종료되었습니다. 아래 버튼을 눌러 디브리핑을 시작하세요.")
        if st.button("디브리핑 보기", disabled=not ready_for_debriefing):
            mark_checklist("12. 성찰: 디브리핑")
            st.session_state.ended = True
            st.session_state.show_debriefing = True
            st.rerun()

    if st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        st.success("프로그램이 종료되었습니다. 아래 질문을 바탕으로 먼저 성찰 답변을 작성해보세요.")
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
        else:
            st.info("답변 작성이 완료되었습니다. 종료 버튼을 누르면 참고 응답 예시를 확인할 수 있습니다.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("종료", disabled=not all_filled):
                mark_checklist("12. 성찰: 디브리핑")
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

        st.markdown("### 🔍 참고 응답 예시 선택 보기")
        st.caption("학습자가 먼저 디브리핑 답변을 완료한 뒤, 자신의 응답을 점검할 수 있도록 참고 예시를 제공합니다.")
        for title, examples in DEBRIEFING_EXAMPLES.items():
            with st.expander(title):
                for example in examples:
                    st.write(f"- {example}")

        if st.button("첫 화면으로 돌아가기"):
            reset_simulation()
            st.rerun()

# ------------------------------------------------------------
# 16. 하단 안내
# ------------------------------------------------------------
st.markdown("---")
st.caption(
    "본 프로토타입은 King의 목표달성이론을 바탕으로 지각 → 판단 → 행위/반응 → 상호작용 → 교류작용 → 목표달성 흐름을 한 방향으로 "
    "AMI 챗봇 가상환자 시뮬레이션 흐름에 반영한 연구용 예시입니다. "
    "검사 설명, 상호작용, 중재 설명은 학생의 짧은 발화를 누적하여 인식하도록 설계되었습니다."
)
