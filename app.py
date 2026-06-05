import os
from html import escape
from typing import Dict, List, Tuple

import streamlit as st
from openai import OpenAI

# ============================================================
# AMI 챗봇 가상환자 시뮬레이션
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
# 3. 앱 제목, 프로그램 설명 토글 및 상황 제시
# ------------------------------------------------------------
st.title("🫀 급성심근경색(AMI) 챗봇 가상환자 시뮬레이션")

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
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)

# 사이드바에서 클릭했을 때만 큰 화면에 프로그램 설명이 나타나도록 설정
show_program_description = st.sidebar.toggle("📘 프로그램 설명 보기", value=False)

PROGRAM_DESCRIPTION = """
이 프로그램은 **King의 목표달성이론을 적용한 AMI 챗봇 가상환자 시뮬레이션 프로토타입**입니다.

**역할 구분**
- **챗봇:** 급성심근경색이 의심되는 62세 남성 환자 *김심근* 역할만 수행합니다.
- **학습자:** 응급실 학생간호사 역할로 환자를 사정하고, 검사와 중재를 설명하며, SBAR 보고와 재사정을 수행합니다.
- **시스템:** 활력징후, 검사결과, 의사 처방만 제시합니다.

**오류 방지 설계**
- 환자 기본정보, 활력징후, 검사결과, 의사 처방, 중재 후 반응은 **고정값**으로 제시됩니다.
- 챗봇은 **의사, 교수자, 평가자 역할을 하지 않으며**, 급성심근경색이 의심되는 환자 역할만 수행합니다.
- 활력징후, 검사결과, 의사 처방은 환자 응답이 아니라 **시스템 정보**로만 제시됩니다.
- 학생이 한 문장으로 완성된 답변을 입력하지 않아도, 짧은 발화를 단계별로 입력하면 프로그램이 이를 **누적 인식**하도록 구성했습니다.
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
- 다만 **검사결과 확인, SBAR 보고, 의사 처방 확인, 중재 수행, 디브리핑**은 정해진 순서에 따라 진행됩니다.
- 각 단계의 해야 할 일과 완료 기준은 왼쪽 진행상태를 클릭하여 확인할 수 있습니다.
"""

if show_program_description:
    st.subheader("📘 프로그램 설명")
    st.markdown(PROGRAM_DESCRIPTION)
    st.info(PROGRESS_DESCRIPTION)
else:
    # 첫 화면은 기존처럼 시뮬레이션 상황을 중심으로 제시
    st.subheader("🚨 시뮬레이션 상황")

    st.markdown("""
    ### 👤 환자 기본정보

    | 항목 | 내용 |
    |---|---|
    | 이름 | 김심근 |
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

    현재 환자는 **가슴 중앙의 압박성 통증**, **턱과 왼쪽 어깨로 퍼지는 방사통**, 
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
    "message": "휴… 아까보다는 좀 나아졌어요. 통증이 8점에서 한 3점 정도로 줄어든 것 같고, 숨쉬기도 조금 편해졌어요… 아직 걱정은 되지만 아까보다 덜 불안해요.",
}

DEBRIEFING_QUESTIONS: List[str] = [
    "환자의 상태를 파악하는 데 가장 중요했던 사정자료는 무엇이었습니까?",
    "검사와 중재의 필요성을 환자에게 어떻게 설명하였으며, 그 설명이 환자의 이해와 참여에 어떤 영향을 주었습니까?",
    "상호작용 단계에서 환자의 문제를 어떻게 확인하고, 간호목표와 목표달성 방법을 어떻게 공유하였습니까?",
    "중재 후 통증, 호흡곤란, 불안 변화와 관련하여 어떤 목표가 달성되었다고 보았습니까?",
]

DEBRIEFING_EXAMPLES: Dict[str, List[str]] = {
    "사정 질문 예시": [
        "가슴 통증이 언제부터 시작되었나요? 위치와 양상은 어떤가요?",
        "통증이 턱이나 어깨로 퍼지나요? 0점부터 10점 중 몇 점 정도인가요?",
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
        "A: NRS 8점 흉통, 좌측 어깨와 턱 방사통, 식은땀, SpO₂ 93%, ECG상 II, III, aVF ST elevation, Troponin I 상승으로 AMI가 의심됩니다.",
        "R: 산소요법, 약물투여 및 추가 처방 확인을 요청드립니다.",
    ],
    "중재 설명 예시": [
        "산소는 숨쉬기 어려운 증상을 완화하고 심장에 산소 공급을 돕기 위해 적용합니다.",
        "니트로글리세린은 흉통 완화에 도움이 될 수 있고, 아스피린은 혈전 생성을 줄이는 데 사용됩니다.",
        "약물 투여 후 어지러움이나 불편감이 있으면 바로 말씀해주세요. 설명드린 중재를 진행해도 괜찮으실까요?",
    ],
    "재사정 예시": [
        "중재 후 가슴 통증은 지금 몇 점 정도인가요?",
        "숨쉬기는 아까보다 편해지셨나요? 불안감은 어느 정도인가요?",
        "다시 통증이 심해지거나 숨이 차면 바로 말씀해주세요.",
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
    "5. 판단: AMI 의심 상황 판단 및 검사 필요성 인식": False,
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

        # 검사 설명 누적 인식
        "ecg_explained": False,
        "blood_test_explained": False,
        "exam_cooperation_requested": False,
        "exam_explained": False,

        # 상호작용 누적 인식
        "problem_identified": False,
        "goal_set": False,
        "means_explained": False,
        "agreement_obtained": False,
        "interaction_completed": False,

        # 중재 설명 누적 인식
        "oxygen_explained": False,
        "medication_explained": False,
        "intervention_purpose_explained": False,
        "side_effect_guidance_given": False,
        "intervention_cooperation_requested": False,
        "intervention_explained": False,

        # 디브리핑
        "show_debriefing": False,
        "debrief_submitted": False,
        "scroll_to_debriefing": False,
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
def patient_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[환자] {text}"}


def system_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[시스템] {text}"}


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


def has_any(text: str, keywords: List[str]) -> bool:
    normalized_text = text.lower()
    return any(keyword.lower() in normalized_text for keyword in keywords)


def count_true(values: List[bool]) -> int:
    return sum(1 for value in values if value)


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
        return "심전도랑 피검사가 왜 필요한지는 이제 조금 이해했어요… 제가 지금 검사에 협조하면 바로 진행할 수 있는 건가요?"
    if updates:
        return "조금 이해됐어요… 그래도 제가 안심하고 협조할 수 있도록 빠진 부분을 한 번만 더 쉽게 설명해 주세요."
    return "선생님… 지금 어떤 검사를 하는 건지 몰라서 더 불안해요. 왜 필요한 검사인지 쉽게 설명해 주시면 협조할게요…"


def get_interaction_patient_response_for_current_state(updates: List[str]) -> str:
    """상호작용 단계에서 현재 누적 상태에 맞는 환자 반응을 반환한다."""
    if st.session_state.problem_identified and not st.session_state.goal_set:
        return "네… 제일 힘든 건 가슴 통증이랑 숨찬 거예요. 그럼 지금 치료 목표는 통증을 줄이고 숨쉬기 편하게 하는 건가요?"
    if st.session_state.goal_set and not st.session_state.problem_identified:
        return "통증을 줄이고 숨쉬기 편해지는 게 목표라는 건 알겠어요… 그런데 지금 제 상태에서 가장 문제가 되는 게 무엇인지 다시 설명해 주세요."
    if (
        st.session_state.problem_identified
        and st.session_state.goal_set
        and not st.session_state.means_explained
    ):
        return "제 문제와 목표는 이해했어요… 그 목표를 위해 앞으로 어떤 치료나 간호를 받게 되는지 알려주세요."
    if (
        st.session_state.problem_identified
        and st.session_state.goal_set
        and st.session_state.means_explained
        and not st.session_state.agreement_obtained
    ):
        return "가슴 통증과 숨찬 증상을 줄이기 위해 산소랑 약물치료가 필요하다는 건 이해했어요… 제가 협조하면 바로 진행할 수 있는 건가요?"
    if updates:
        return "조금 이해됐어요… 제 문제, 치료 목표, 그리고 앞으로 받을 방법을 한 번만 더 연결해서 설명해 주세요."
    return "선생님… 검사 결과가 안 좋다고 하니 너무 불안해요. 지금 제 문제와 치료 목표를 쉽게 설명해 주세요…"


def get_intervention_patient_response_for_current_state(updates: List[str]) -> str:
    """중재 설명 단계에서 현재 누적 상태에 맞는 환자 반응을 반환한다."""
    if st.session_state.oxygen_explained and not st.session_state.medication_explained:
        return "산소가 숨쉬는 데 도움이 된다는 건 알겠어요… 그런데 약은 어떤 약이고 왜 필요한가요?"
    if st.session_state.medication_explained and not st.session_state.oxygen_explained:
        return "약이 가슴 통증을 줄이는 데 도움이 된다는 건 알겠어요… 산소는 왜 필요한지도 쉽게 설명해 주세요."
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
        and not st.session_state.intervention_cooperation_requested
    ):
        return "불편하면 말씀드리면 되는 것도 알겠어요… 그럼 지금 제가 동의하면 바로 진행하는 건가요?"
    if updates:
        return "조금 이해됐어요… 제가 빠뜨린 부분 없이 안심하고 협조할 수 있도록 한 번만 더 쉽게 설명해 주세요."
    return "선생님… 지금 무엇을 하는 건지 조금 불안해요. 산소와 약이 왜 필요한지 쉽게 설명해 주시면 협조할게요…"



def doctor_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[의사 처방] {text}"}


def feedback_message(text: str) -> Dict[str, str]:
    return {"role": "assistant", "content": f"[학습 안내] {text}"}



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
            value="62세 남성 김심근 환자가 30분 전부터 흉통과 호흡곤란을 호소합니다.",
            height=80,
        )
        b_text = st.text_area(
            "B | Background 배경",
            value="고혈압 과거력, 흡연력, 부친 심장마비 가족력이 있습니다.",
            height=80,
        )
        a_text = st.text_area(
            "A | Assessment 사정",
            value="NRS 8점 흉통, 좌측 어깨와 턱 방사통, 식은땀, SpO₂ 93%, ECG상 II, III, aVF ST elevation, Troponin I 상승으로 AMI가 의심됩니다.",
            height=100,
        )
        r_text = st.text_area(
            "R | Recommendation 제안",
            value="산소요법, 약물투여 및 추가 처방 확인을 요청드립니다.",
            height=80,
        )

        col_submit, col_close = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("📞 SBAR 보고 제출")
        with col_close:
            closed = st.form_submit_button("닫기")

        if submitted:
            sbar_report = (
                "SBAR 보고\n"
                f"S: {s_text}\n"
                f"B: {b_text}\n"
                f"A: {a_text}\n"
                f"R: {r_text}"
            )
            st.session_state.messages.append({"role": "user", "content": f"☎️ [SBAR 보고]\n{sbar_report}"})
            for answer in get_response(sbar_report):
                st.session_state.messages.append(answer)
            st.session_state.show_sbar_window = False
            st.rerun()

        if closed:
            st.session_state.show_sbar_window = False
            st.rerun()



def render_message(msg: Dict[str, str]) -> None:
    """챗봇, 학습자, 시스템 정보를 색상과 라벨로 명확히 구분한다."""
    raw = msg.get("content", "")
    role = msg.get("role", "assistant")

    # 기본값
    label = "안내"
    body = raw
    bg = "#F8F9FA"
    border = "#ADB5BD"
    emoji = "ℹ️"

    # 학습자 입력
    if role == "user":
        label = "학생간호사"
        body = raw
        bg = "#E8F1FF"
        border = "#4C8DFF"
        emoji = "🧑‍⚕️"

    # 챗봇 환자 응답
    elif raw.startswith("[환자]"):
        label = "챗봇 환자 김심근"
        body = raw.replace("[환자]", "", 1).strip()
        bg = "#FFF4E6"
        border = "#F59F00"
        emoji = "🫀"

    # 시스템: 활력징후
    elif raw.startswith("[활력징후]"):
        label = "시스템 | 활력징후"
        body = raw.replace("[활력징후]", "", 1).strip()
        bg = "#F1F3F5"
        border = "#495057"
        emoji = "📊"

    # 시스템: 검사결과
    elif raw.startswith("[검사결과]"):
        label = "시스템 | 검사결과"
        body = raw.replace("[검사결과]", "", 1).strip()
        bg = "#F1F3F5"
        border = "#495057"
        emoji = "🧪"

    # 시스템: 의사 처방
    elif raw.startswith("[의사 처방]"):
        label = "시스템 | 의사 처방"
        body = raw.replace("[의사 처방]", "", 1).strip()
        bg = "#F1F3F5"
        border = "#495057"
        emoji = "💊"

    # 시뮬레이션 완료 안내
    elif raw.startswith("[완료 안내]"):
        label = "시뮬레이션 완료"
        body = raw.replace("[완료 안내]", "", 1).strip()
        bg = "#F1F3F5"
        border = "#495057"
        emoji = "✅"

    # 기존 [시스템] 메시지 중 객관적 임상자료는 표시하고, 진행 조건 안내는 숨김
    elif raw.startswith("[시스템]"):
        system_body = raw.replace("[시스템]", "", 1).strip()

        if system_body.startswith("의사 처방") or "O₂" in system_body or "NTG" in system_body or "Aspirin" in system_body:
            label = "시스템 | 의사 처방"
            body = system_body
            bg = "#F1F3F5"
            border = "#495057"
            emoji = "💊"
        elif system_body.startswith("초기 활력징후") or "BP:" in system_body or "SpO₂" in system_body:
            label = "시스템 | 활력징후"
            body = system_body
            bg = "#F1F3F5"
            border = "#495057"
            emoji = "📊"
        elif system_body.startswith("검사결과") or "Troponin" in system_body or "CK-MB" in system_body:
            label = "시스템 | 검사결과"
            body = system_body
            bg = "#F1F3F5"
            border = "#495057"
            emoji = "🧪"
        else:
            return

    # 학습 안내는 표시하지 않음
    elif raw.startswith("[학습 안내]"):
        return

    text_color = "#111827"
    subtext_color = "#374151"

    html = f"""
    <div style="background:{bg}; border-left:5px solid {border}; padding:2px 12px;
                border-radius:8px; margin:2px 0; line-height:1.18; white-space:pre-wrap;
                color:{text_color}; box-shadow:0 1px 2px rgba(0,0,0,0.07);
                font-size:1.5rem; width:100%;">
        <div style="font-weight:800; margin-bottom:0px; color:{text_color}; font-size:1.5rem;">
            {emoji} {escape(label)}
        </div>
        <div style="color:{subtext_color}; font-size:1.5rem;">{escape(body)}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def get_current_guidance() -> str:
    """처음 문구를 반복하지 않고 현재 단계에 맞는 재질문/안내를 제공한다."""
    if not st.session_state.intro_done:
        return "먼저 자기소개와 환자 확인을 해보세요. 예: ‘안녕하세요, 학생간호사입니다. 성함이 어떻게 되세요?’"
    if not st.session_state.pain_symptom_done:
        return "현재 단계에서는 통증 위치, 양상, 시작 시점, NRS 점수, 방사통, 동반증상을 확인해보세요."
    if not st.session_state.vitals_done:
        return "다음으로 활력징후를 확인해보세요. 예: ‘현재 활력징후를 확인하겠습니다.’"
    if not st.session_state.history_risk_done:
        return "과거력, 복용약, 흡연력, 가족력, 알레르기 여부 등 위험요인을 확인해보세요."
    if not st.session_state.ami_judged:
        return "수집한 자료를 바탕으로 AMI 가능성을 판단하고, 심전도와 심근효소 검사의 필요성을 인식해보세요."
    if not st.session_state.exam_explained:
        return "심전도와 혈액검사가 왜 필요한지 설명하고, 환자의 이해와 검사 참여 의사를 확인해보세요."
    if not st.session_state.labs_shown:
        return "검사 설명과 참여 확인이 완료되었습니다. 이제 검사결과를 확인해보세요."
    if not st.session_state.interaction_completed:
        return "검사결과를 바탕으로 환자 문제를 확인하고, 간호목표와 목표달성 방법을 환자에게 쉽게 공유해보세요."
    if not st.session_state.sbar_reported:
        return "SBAR 형식으로 환자 상태, 배경, 사정 결과, 제안을 포함하여 의사에게 보고해보세요."
    if not st.session_state.intervention_explained:
        return "의사 처방을 바탕으로 산소요법과 약물의 목적을 설명하고, 환자의 이해와 참여 의사를 확인해보세요."
    if not st.session_state.intervention_done:
        return "이제 처방에 따라 산소요법, NTG, Aspirin, 12-lead ECG 재확인을 수행해보세요."
    if not st.session_state.reassessment_done:
        return "중재 후 통증, 호흡곤란, 불안 정도를 재사정해보세요."
    return "시뮬레이션 흐름은 완료되었습니다. 디브리핑에서 수행 과정을 성찰해보세요."


STEP_HELP: Dict[str, Tuple[str, str]] = {
    "1. 지각: 초기 접촉 및 주호소 확인": ("환자에게 자기소개를 하고 환자 확인과 주호소를 확인합니다.", "자기소개 또는 환자 확인이 이루어지면 완료됩니다."),
    "2. 지각: 통증 및 동반 증상 사정": ("통증 위치, 양상, 시작 시점, NRS, 방사통, 호흡곤란, 식은땀, 불안을 사정합니다.", "통증/동반증상 관련 질문이 입력되면 완료됩니다."),
    "3. 지각: 활력징후 확인": ("혈압, 맥박, 호흡수, 산소포화도, 체온을 확인합니다.", "활력징후 확인 요청 시 시스템이 수치를 제시하면 완료됩니다."),
    "4. 지각: 병력 및 위험요인 사정": ("고혈압, 복용약, 흡연력, 가족력, 알레르기 등을 확인합니다.", "병력 또는 위험요인 관련 질문이 입력되면 완료됩니다."),
    "5. 판단: AMI 의심 상황 판단 및 검사 필요성 인식": ("수집한 자료를 바탕으로 AMI 가능성과 ECG/심근효소 검사 필요성을 판단합니다.", "AMI 가능성 또는 검사 필요성을 언급하면 완료됩니다."),
    "6. 행위/반응: 검사 필요성 설명 및 환자의 이해·참여 확인": ("ECG와 혈액검사의 필요성을 쉽게 설명하고 환자의 이해와 참여 의사를 확인합니다.", "심전도 설명, 혈액검사 설명, 검사 참여 확인이 모두 인식되면 완료됩니다."),
    "7. 상호작용: 검사결과 기반 문제 구체화": ("검사결과를 확인하고 환자의 주요 문제를 구체화합니다.", "검사결과 확인 후 완료됩니다."),
    "8. 상호작용: 간호목표 공유 및 목표달성 방법 확인": ("환자 문제, 간호목표, 목표달성 방법을 환자에게 공유하고 이해와 참여를 확인합니다.", "문제 확인, 목표 공유, 방법 설명, 참여 확인이 모두 인식되면 완료됩니다."),
    "9. 교류작용: SBAR 보고 및 처방 확인": ("SBAR로 의사에게 보고하고 처방을 확인합니다.", "SBAR 보고 내용이 인식되면 시스템/의사 처방이 제시되고 완료됩니다."),
    "10. 교류작용: 중재 설명 및 중재 수행": ("산소요법과 약물 중재를 설명하고 처방에 따라 수행합니다.", "중재 설명 후 처방 기반 중재 수행이 이루어지면 완료됩니다."),
    "11. 목표달성: 중재 후 재사정 및 목표달성 확인": ("중재 후 통증, 호흡곤란, 불안 변화를 재사정합니다.", "중재 후 상태 변화 확인이 이루어지면 완료됩니다."),
    "12. 성찰: 디브리핑": ("사정, 판단, 설명, 보고, 중재, 재사정 과정을 성찰합니다.", "디브리핑을 열고 답변을 작성하면 완료됩니다."),
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
    """심전도 설명, 혈액검사 설명, 협조 요청을 누적 인식한다."""
    updates = []

    # 검사명만 나열한 경우와 실제 설명을 구분한다.
    # 예: "심전도와 혈액검사가 필요합니다"만으로는 검사 설명 완료로 보지 않는다.
    ecg_name_keywords = [
        "심전도", "ecg", "ekg", "12유도", "12-lead",
        "electrocardiogram", "electrocardiography"
    ]
    ecg_explain_keywords = [
        "심장 전기", "전기적 변화", "전기 신호", "전기 활동",
        "심장 상태", "심장 확인", "심장 상태 확인",
        "심장 리듬", "심장 박동", "심장의 변화",
        "heart condition", "heart status", "electrical changes", "electrical activity",
        "heart rhythm", "heart signal"
    ]

    blood_name_keywords = [
        "혈액검사", "혈액 검사", "피검사", "채혈", "심근효소",
        "blood test", "blood work", "cardiac enzyme", "myocardial enzyme"
    ]
    blood_explain_keywords = [
        "트로포닌", "troponin", "ck-mb", "ckmb",
        "심장근육 손상", "심근 손상", "심장 근육 손상",
        "심근효소 수치", "효소 수치", "관련 수치", "손상 여부",
        "heart muscle damage", "myocardial damage", "cardiac muscle damage",
        "enzyme level", "damage to the heart muscle"
    ]

    cooperation_keywords = [
        "협조", "협조 요청", "협조해 주실 수", "협조해주시겠",
        "동의", "괜찮을까요", "괜찮으실까요",
        "진행해도", "진행해도 될까요", "검사해도 될까요",
        "검사를 진행", "검사 진행", "진행하겠습니다",
        "설명 들었으면", "이해되셨으면",
        "cooperate", "cooperation", "agree", "consent", "proceed",
        "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]

    # 심전도는 검사명 + 목적/내용 설명이 함께 들어와야 설명으로 인정한다.
    if has_any(text, ecg_name_keywords) and has_any(text, ecg_explain_keywords):
        st.session_state.ecg_explained = True
        updates.append("심전도 검사 설명")

    # 혈액검사는 검사명 또는 심근효소 표현 + 손상 여부/수치 설명이 들어와야 설명으로 인정한다.
    if (
        has_any(text, blood_name_keywords) and has_any(text, blood_explain_keywords)
    ) or (
        has_any(text, ["트로포닌", "troponin", "ck-mb", "ckmb", "심근효소", "cardiac enzyme", "myocardial enzyme"])
        and has_any(text, ["심장근육 손상", "심근 손상", "손상 여부", "수치", "확인",
                           "heart muscle damage", "damage", "level", "check", "determine"])
    ):
        st.session_state.blood_test_explained = True
        updates.append("혈액검사 설명")

    # 검사 참여 확인은 심전도와 혈액검사 설명이 모두 끝난 뒤에만 인정한다.
    if (
        st.session_state.ecg_explained
        and st.session_state.blood_test_explained
        and has_any(text, cooperation_keywords)
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
        mark_checklist("6. 행위/반응: 검사 필요성 설명 및 환자의 이해·참여 확인")

    return updates


def update_interaction_state(text: str) -> List[str]:
    """문제 확인, 목표 설정, 방법 제시, 합의/협조 확인을 누적 인식한다."""
    updates = []

    # 12명 사전 트리거 자료 + King 상호작용 4요소 반영
    problem_keywords = [
        "문제", "현재 문제", "가장 힘든", "가장 큰 문제",
        "가슴 통증", "흉통", "가슴 답답", "답답",
        "숨찬", "숨참", "호흡곤란", "불안", "불안 정도",
        "검사결과", "검사 결과", "결과 토대로", "환자 상태", "상태 판단",
        "의미있는 자료", "의미 있는 자료"
    ]
    goal_keywords = [
        "목표", "공동 목표", "함께 목표",
        "통증을 줄", "통증 감소", "통증 완화", "흉통 완화",
        "숨쉬기 편", "숨 쉬기 편", "호흡을 편", "호흡곤란 완화",
        "불안을 줄", "불안 완화", "불안 감소", "안정"
    ]
    means_keywords = [
        "이를 위해", "방법", "필요한 이유", "다음 조치", "우선 조치",
        "처치 필요", "산소", "산소요법", "산소 공급", "산소공급",
        "약물", "약", "약물 치료", "약물 투여", "약물 작용",
        "니트로", "니트로글리세린", "ntg",
        "아스피린", "aspirin", "아스피린 중재",
        "심전도", "처치", "중재", "치료", "진행", "시행", "적용"
    ]
    agreement_keywords = [
        "협조", "환자 협조", "협조 요청",
        "협조해 주실 수", "협조해주시겠", "협조해 주시겠",
        "치료에 협조", "방법에 협조",
        "동의", "동의하시", "동의하시면",
        "괜찮을까요", "괜찮으실까요",
        "진행해도", "진행해도 괜찮", "진행해도 될까요",
        "해도 될까요", "이 방법으로", "이렇게 진행",
        "이해되도록", "함께", "같이"
    ]

    if has_any(text, problem_keywords):
        st.session_state.problem_identified = True
        updates.append("환자 문제 확인")
    if has_any(text, goal_keywords):
        st.session_state.goal_set = True
        updates.append("간호목표 공유")
    if has_any(text, means_keywords):
        st.session_state.means_explained = True
        updates.append("목표달성 방법 설명")
    if has_any(text, agreement_keywords):
        st.session_state.agreement_obtained = True
        updates.append("이해·참여 확인")

    # King의 목표달성이론에서 상호작용은 문제 확인, 간호목표 공유,
    # 목표달성 방법 설명, 이해·참여 확인이 모두 포함되어야 하므로
    # 4요소가 모두 충족될 때 상호작용 완료로 인정한다.
    if (
        st.session_state.problem_identified
        and st.session_state.goal_set
        and st.session_state.means_explained
        and st.session_state.agreement_obtained
    ):
        st.session_state.interaction_completed = True
        st.session_state.cooperation_formed = True
        mark_checklist("8. 상호작용: 간호목표 공유 및 목표달성 방법 확인")

    return updates


def update_intervention_explanation_state(text: str) -> List[str]:
    """산소, 약물, 목적, 이상반응 안내, 협조 요청을 누적 인식한다."""
    updates = []

    # 단어만 포함된 경우와 실제 설명을 구분한다.
    # 예: "산소를 투여하겠습니다"만으로는 산소요법 설명 완료로 보지 않는다.
    oxygen_name_keywords = [
        "산소", "산소요법", "o2", "o₂", "비강캐뉼라", "비강 캐뉼라",
        "oxygen", "nasal cannula"
    ]
    oxygen_explain_keywords = [
        "숨쉬기", "숨 쉬기", "호흡", "호흡곤란", "숨찬", "숨 차",
        "산소 공급", "산소공급", "심장에 산소", "심장 부담", "부담을 줄",
        "완화", "도움", "편하게",
        "breathing", "shortness of breath", "supply oxygen", "oxygen supply",
        "help the heart", "strain on the heart", "relieve", "ease breathing"
    ]

    medication_name_keywords = [
        "약", "약물", "니트로", "니트로글리세린", "ntg",
        "아스피린", "aspirin",
        "medicine", "medication", "drug", "nitroglycerin"
    ]
    medication_explain_keywords = [
        "통증", "흉통", "가슴 통증", "통증 완화", "통증 감소",
        "혈전", "혈전 예방", "혈전 생성", "혈관확장", "혈관 확장",
        "줄이는", "줄이는 데", "도움", "예방",
        "chest pain", "pain", "relieve pain", "reduce pain",
        "blood clot", "clot", "prevent clot", "reduce clot", "vasodilation",
        "widen blood vessel", "help reduce"
    ]

    purpose_keywords = [
        "통증", "흉통", "가슴 통증", "호흡곤란", "숨쉬기", "숨 쉬기",
        "완화", "줄", "도움", "심장 부담", "혈전 예방",
        "chest pain", "shortness of breath", "breathing", "relieve",
        "reduce", "help", "strain on the heart", "blood clot"
    ]

    side_effect_keywords = [
        "어지럽", "어지러움", "두통", "불편", "불편감", "이상", "부작용",
        "통증 악화", "호흡곤란", "숨이 더 차", "말씀", "알려",
        "바로 말", "바로 말씀", "불편하면", "불편하면 말씀",
        "dizzy", "dizziness", "headache", "uncomfortable", "discomfort",
        "side effect", "worsening pain", "difficulty breathing", "tell me",
        "let me know", "notify", "right away"
    ]
    cooperation_keywords = [
        "협조", "협조해 주실 수", "협조해주시겠", "협조해 주시겠",
        "동의", "동의하시", "동의하시면",
        "괜찮을까요", "괜찮으실까요",
        "진행해도", "진행해도 괜찮", "진행해도 될까요",
        "해도 될까요", "이 방법으로", "이렇게 진행",
        "cooperate", "cooperation", "agree", "consent", "proceed",
        "can we proceed", "may i proceed", "is it okay", "okay to proceed"
    ]

    oxygen_explained_now = has_any(text, oxygen_name_keywords) and has_any(text, oxygen_explain_keywords)
    medication_explained_now = has_any(text, medication_name_keywords) and has_any(text, medication_explain_keywords)

    if oxygen_explained_now:
        st.session_state.oxygen_explained = True
        updates.append("산소요법 설명")

    if medication_explained_now:
        st.session_state.medication_explained = True
        updates.append("약물투여 설명")

    # 중재 목적은 산소 또는 약물 설명과 관련 목적 표현이 포함된 경우에 인정한다.
    if (oxygen_explained_now or medication_explained_now) and has_any(text, purpose_keywords):
        st.session_state.intervention_purpose_explained = True
        updates.append("중재 목적 설명")

    # 이상반응/불편감 안내는 산소와 약물 설명이 모두 이루어진 뒤에만 인정한다.
    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and has_any(text, side_effect_keywords)
    ):
        st.session_state.side_effect_guidance_given = True
        updates.append("이상반응/불편감 안내")

    # 중재 참여 확인은 산소, 약물, 목적, 이상반응/불편감 안내가 모두 이루어진 뒤에만 인정한다.
    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and st.session_state.side_effect_guidance_given
        and has_any(text, cooperation_keywords)
    ):
        st.session_state.intervention_cooperation_requested = True
        updates.append("중재 참여 확인")

    if (
        st.session_state.oxygen_explained
        and st.session_state.medication_explained
        and st.session_state.intervention_purpose_explained
        and st.session_state.intervention_cooperation_requested
    ):
        st.session_state.intervention_explained = True

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

    intro_keywords = [
        "안녕하세요", "학생간호사", "간호학생", "담당 간호사", "담당 학생",
        "제가 도와드리겠습니다", "제가 확인하겠습니다", "제가 사정하겠습니다",
        "성함이 어떻게 되세요", "이름이 어떻게 되세요", "환자분 성함", "김심근님 맞으세요"
    ]
    if has_any(text, intro_keywords):
        return "intro"

    # 재사정은 중재 후에만 우선 인정
    reassess_keywords = [
        "재사정", "다시 확인", "상태를 다시", "치료 후", "중재 후", "처치 후",
        "통증 변화", "통증 감소", "지금 통증", "통증은 지금",
        "가슴통증 몇 점", "가슴 통증 몇 점", "몇 점", "nrs", "통증척도",
        "호흡 상태", "호흡은", "숨쉬기", "숨 쉬기", "숨 쉬는 건 괜찮",
        "숨쉬는 건 괜찮", "불편감", "불안 정도", "불안은",
        "불안 완화", "불안 감소", "어떠세요", "나아졌", "완화"
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
        "불편", "부작용", "증상 있으면", "알려주세요", "말씀해주세요"
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
        "목표", "공동 목표", "통증을 줄", "통증 완화", "통증 감소",
        "숨쉬기 편", "숨 쉬기 편", "호흡을 편", "호흡곤란 완화",
        "불안", "불안 완화", "불안 감소", "안정",
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
        "아스피린", "aspirin", "아스피린 중재", "혈전 예방",
        "통증", "통증 감소", "호흡", "숨쉬기", "불편", "어지럽", "부작용",
        "불편하면 말씀", "환자 협조", "이해되도록 설명",
        "진행해도", "진행해도 괜찮", "진행해도 될까요",
        "괜찮을까요", "괜찮으실까요", "협조"
    ]
    intervention_do_keywords = [
        "처방에 따라", "처방대로", "시행하겠습니다", "수행하겠습니다", "진행하겠습니다",
        "이제 진행", "처치하겠습니다", "중재하겠습니다",
        "산소 투여", "산소를 투여", "산소 적용", "산소 연결",
        "산소요법 시행", "산소 요법 시행",
        "비강캐뉼라", "비강 캐뉼라", "ntg 투여", "니트로 투여", "니트로글리세린 투여",
        "아스피린 투여", "약물을 투여", "약물 투여", "12-lead", "12유도",
        "심전도 재확인", "ecg re-check", "ekg re-check"
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

    # AMI 가능성 판단
    ami_judgment_keywords = [
        "급성심근경색 가능성", "급성심근경색 의심", "ami 가능성", "ami 의심",
        "심근경색 가능성", "심근경색 의심", "stemi 가능성", "stemi 의심",
        "심장 문제 가능성", "심장 혈관 문제", "심혈관 문제", "심장 쪽 문제",
        "수집한 자료를 종합", "자료를 종합", "증상과 위험요인", "위험요인",
        "현재 증상으로 보아", "현재 증상으로 봤을 때", "심장 상태 확인이 필요"
    ]
    if has_any(text, ami_judgment_keywords):
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
        "복용약", "복용약물", "현재 복용 약물", "약 드시", "약 먹",
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
        "심전도", "ecg", "ekg", "12유도", "12-lead",
        "혈액검사", "혈액 검사", "피검사", "채혈", "심근효소",
        "검사", "정확한 상태 파악", "상태 확인", "정밀한 진단",
        "관련 수치", "전기적 변화", "심장근육 손상", "심근 손상",
        "트로포닌", "troponin", "ck-mb", "ckmb",
        "알기 쉽게", "알아듣기 쉽게", "이해하기 쉽게",
        "납득할 수 있도록", "협조", "협조 요청", "불안 완화"
    ]
    if not st.session_state.exam_explained and has_any(text, exam_keywords):
        return "exam_explanation"

    # 검사결과 확인/임상 판단: 검사 설명이 완료된 이후에만 검사결과 확인으로 분류한다.
    labs_keywords = [
        "검사결과", "검사 결과", "검사수치", "검사 수치",
        "결과 확인", "결과 해석", "결과 토대로",
        "심전도 결과", "혈액검사 결과", "lab",
        "환자 상태", "상태 판단", "정상 수치", "정상범위",
        "비정상 수치", "이상 수치", "의미있는 자료", "의미 있는 자료",
        "st 상승", "st분절", "st 분절", "troponin", "트로포닌",
        "ck-mb", "ckmb", "ami", "ami 의심", "급성심근경색",
        "심근경색", "stemi", "유추되는 질환명", "감별진단",
        "다른 질병", "다음 조치", "우선 조치", "처치 필요"
    ]
    if st.session_state.exam_explained and has_any(text, labs_keywords):
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
        "턱", "왼쪽 어깨", "어깨", "동반 증상", "다른 증상",
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


# ------------------------------------------------------------
# 11. 응답 생성
# ------------------------------------------------------------
def get_response(user_text: str) -> List[Dict[str, str]]:
    category = classify_input(user_text)
    responses: List[Dict[str, str]] = []

    if category == "intro":
        st.session_state.intro_done = True
        mark_checklist("1. 지각: 초기 접촉 및 주호소 확인")
        responses.append(patient_message(
            "네… 김심근입니다. 가슴 한가운데가 너무 꽉 조여요… 숨도 차고 식은땀이 나요. 저 이러다 큰일 나는 거 아니죠?"
        ))

    elif category == "pain_assessment":
        st.session_state.pain_symptom_done = True
        mark_checklist("2. 지각: 통증 및 동반 증상 사정")
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
        elif has_any(user_text, ["숨", "숨참", "호흡곤란", "식은땀", "동반", "다른 증상", "불안"]):
            fact = PATIENT_INFO["associated_symptoms"]
        else:
            fact = f"{PATIENT_INFO['chief_complaint']} 통증은 {PATIENT_INFO['pain_score_initial']} 정도이다."
        responses.append(patient_message(naturalize_with_openai(user_text, fact, tone="극심한 흉통과 불안 상태")))

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
        responses.append(patient_message(naturalize_with_openai(user_text, PATIENT_INFO["family_history"], tone="불안하지만 질문에는 답하는 상태")))

    elif category == "history":
        st.session_state.history_risk_done = True
        mark_checklist("4. 지각: 병력 및 위험요인 사정")
        if "알레르기" in user_text:
            fact = PATIENT_INFO["allergy"]
        elif has_any(user_text, ["약", "복용", "복용약물", "혈압약"]):
            fact = PATIENT_INFO["medication"]
        elif has_any(user_text, ["담배", "흡연"]):
            fact = PATIENT_INFO["smoking"]
        elif has_any(user_text, ["음주", "술"]):
            fact = PATIENT_INFO["alcohol"]
        elif has_any(user_text, ["식습관", "생활습관"]):
            fact = PATIENT_INFO["diet"]
        elif has_any(user_text, ["운동"]):
            fact = PATIENT_INFO["exercise"]
        elif has_any(user_text, ["당뇨"]):
            fact = PATIENT_INFO["diabetes"]
        elif has_any(user_text, ["고지혈증"]):
            fact = PATIENT_INFO["hyperlipidemia"]
        else:
            fact = f"{PATIENT_INFO['history']}. {PATIENT_INFO['medication']}"
        responses.append(patient_message(naturalize_with_openai(user_text, fact, tone="불안하지만 질문에는 답하는 상태")))

    elif category == "ami_judgment":
        st.session_state.ami_judged = True
        mark_checklist("5. 판단: AMI 의심 상황 판단 및 검사 필요성 인식")
        responses.append(patient_message(
            "심장 문제일 수도 있다는 건가요…? 너무 무서워요. 그래도 정확히 확인하려면 심전도랑 피검사를 해야 한다는 말씀이시죠?"
        ))
        responses.append(system_message(
            "AMI 가능성 인식이 확인되었습니다. 심전도와 혈액검사의 필요성을 환자에게 설명하고 협조를 구하세요."
        ))

    elif category == "exam_explanation":
        updates = update_exam_explanation_state(user_text)

        if st.session_state.exam_explained:
            responses.append(patient_message(
                "아… 심전도는 심장 상태를 보고, 피검사는 심장근육 손상 여부를 확인하는 거군요. "
                "무섭긴 하지만 설명 들었으니까 검사 진행해 주세요…"
            ))
            responses.append(system_message("검사 설명 및 이해와 참여 확인이 완료되었습니다. 검사결과를 확인할 수 있습니다."))
        else:
            responses.append(patient_message(get_exam_patient_response_for_current_state(updates)))

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
                f"- Troponin I: {LAB_RESULTS['Troponin I']}\n"
                f"- CK-MB: {LAB_RESULTS['CK-MB']}"
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
                responses.append(patient_message(
                    "네… 제 문제는 가슴 통증과 숨찬 증상이고, 목표는 통증을 줄이고 숨쉬기 편해지는 거군요. "
                    "산소와 약물치료가 필요하다는 것도 이해했어요… 말씀하신 방법에 협조할게요."
                ))
                responses.append(system_message(
                    "상호작용 단계가 완료되었습니다. 다음 단계로 SBAR 보고를 진행하세요."
                ))
            else:
                responses.append(patient_message(get_interaction_patient_response_for_current_state(updates)))

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
                "의사 처방\\n"
                + "\\n".join([f"{idx}. {order}" for idx, order in enumerate(DOCTOR_ORDER, start=1)])
            )
            responses.append(order_message(order_text))

    elif category == "intervention_explanation":
        if not st.session_state.order_shown:
            responses.append(system_message("중재 설명 전 SBAR 보고를 완료하고 의사 처방을 먼저 확인해야 합니다."))
        else:
            updates = update_intervention_explanation_state(user_text)

            if st.session_state.intervention_explained:
                st.session_state.cooperation_formed = True
                mark_checklist("10. 교류작용: 중재 설명 및 중재 수행")
                responses.append(patient_message(
                    "네… 설명 들으니 조금 안심돼요. 불편하거나 어지러우면 바로 말씀드릴게요… 진행해 주세요."
                ))
            else:
                responses.append(patient_message(get_intervention_patient_response_for_current_state(updates)))
    elif category == "intervention":
        if not st.session_state.order_shown:
            responses.append(system_message("아직 의사 처방이 제시되지 않았습니다. SBAR 보고 후 처방을 확인하세요."))
        elif not st.session_state.intervention_explained:
            responses.append(patient_message(
                "선생님… 산소와 약을 바로 하기 전에 왜 필요한지, 불편하면 어떻게 해야 하는지 설명해 주세요. "
                "설명 듣고 진행해도 되는지 말씀드릴게요…"
            ))
            responses.append(system_message("중재 수행 전 산소 설명, 약물 설명, 중재 목적 설명, 환자의 이해와 참여 확인이 필요합니다."))
        else:
            st.session_state.intervention_done = True
            st.session_state.cooperation_formed = True
            mark_checklist("10. 교류작용: 중재 설명 및 중재 수행")
            responses.append(order_message(
                "처방 기반 중재 수행\n"
                f"- {DOCTOR_ORDER[0]}\n"
                f"- {DOCTOR_ORDER[1]}\n"
                f"- {DOCTOR_ORDER[2]}\n"
                f"- {DOCTOR_ORDER[3]}"
            ))
            responses.append(patient_message("네… 설명 들었으니까 진행해주세요. 아직 무섭긴 한데, 선생님 말씀 믿고 해볼게요…"))
            responses.append(system_message("5분 후 환자 상태를 재사정하세요."))

    elif category == "reassessment":
        st.session_state.reassessment_done = True
        st.session_state.goal_achieved = True
        mark_checklist("11. 목표달성: 중재 후 재사정 및 목표달성 확인")
        if has_any(user_text, ["통증", "몇 점", "nrs"]):
            responses.append(patient_message("아까보다는 훨씬 나아요… 지금은 한 3점 정도인 것 같아요. 그래도 아직 조금 답답하긴 해요."))
        elif has_any(user_text, ["숨", "호흡"]):
            responses.append(patient_message("숨쉬는 건 조금 편해졌어요… 아까처럼 막 숨이 막히는 느낌은 덜해요."))
        elif has_any(user_text, ["불안", "무섭"]):
            responses.append(patient_message("아직 겁은 나는데요… 그래도 설명 듣고 처치를 받으니까 아까보다는 덜 불안해요."))
        else:
            responses.append(patient_message(POST_INTERVENTION_STATUS["message"]))

        st.session_state.ended = True
        st.session_state.scroll_to_debriefing = True
        responses.append(completion_message(
            "중재 후 재사정과 목표달성 확인이 완료되었습니다. "
            "시뮬레이션이 종료되었습니다. 아래 디브리핑 단계로 이동하여 "
            "환자 사정, 판단, 검사 및 중재 설명, SBAR 보고, 중재 수행, 재사정 과정을 성찰해 주세요."
        ))

    elif category == "closing_therapeutic":
        responses.append(patient_message("네… 다시 아프거나 숨이 차면 바로 말씀드릴게요. 옆에서 봐주시니까 조금 안심돼요…"))

    elif category == "therapeutic":
        responses.append(patient_message("그렇게 말씀해주시니까 조금은 안심돼요… 그래도 가슴이 계속 답답해서 아직 무서워요."))

    else:
        # 시뮬레이션 중에는 정답 예시나 학습 안내를 보여주지 않고,
        # 현재 단계에 맞춰 환자가 자연스럽게 되묻도록 한다.
        if st.session_state.ami_judged and not st.session_state.exam_explained:
            responses.append(patient_message(get_exam_patient_response_for_current_state([])))
        elif st.session_state.labs_shown and not st.session_state.interaction_completed:
            responses.append(patient_message(get_interaction_patient_response_for_current_state([])))
        elif st.session_state.order_shown and not st.session_state.intervention_explained:
            responses.append(patient_message(get_intervention_patient_response_for_current_state([])))
        else:
            responses.append(patient_message("네… 제가 잘 이해하지 못했어요. 다시 한 번 쉽게 말씀해 주실 수 있을까요?"))

    return responses


# ------------------------------------------------------------
# 12. 세션 초기화 및 사이드바
# ------------------------------------------------------------
init_state()

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
    st.write(f"{'✅' if st.session_state.means_explained else '⬜'} 목표달성 방법 설명")
    st.write(f"{'✅' if st.session_state.agreement_obtained else '⬜'} 환자의 이해와 참여 확인")

with st.sidebar.expander("중재 설명 세부 항목", expanded=False):
    st.write(f"{'✅' if st.session_state.oxygen_explained else '⬜'} 산소요법 설명")
    st.write(f"{'✅' if st.session_state.medication_explained else '⬜'} 약물투여 설명")
    st.write(f"{'✅' if st.session_state.intervention_purpose_explained else '⬜'} 중재 목적 설명")
    st.write(f"{'✅' if st.session_state.side_effect_guidance_given else '⬜'} 이상반응/불편감 안내")
    st.write(f"{'✅' if st.session_state.intervention_cooperation_requested else '⬜'} 중재 참여 확인")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 목표 달성 지표")
st.sidebar.write(f"{'✅' if st.session_state.cooperation_formed else '⬜'} 환자의 이해와 참여 확인")
st.sidebar.write(f"{'✅' if st.session_state.intervention_done else '⬜'} 처방 기반 중재 수행")
st.sidebar.write(f"{'✅' if st.session_state.goal_achieved else '⬜'} 통증·호흡곤란·불안 완화 확인")

# ------------------------------------------------------------
# 13. 시작 / 초기화 버튼
# ------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("▶ 시뮬레이션 시작"):
        reset_simulation()
        st.session_state.started = True
        st.session_state.messages.append(patient_message(
            "허억… 선생님… 가슴이 너무 꽉 조여요. 숨도 차고 식은땀이 나요… 저 이러다 죽는 거 아니죠?"
        ))
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
                "의사 처방\\n"
                + "\\n".join([f"{idx}. {order}" for idx, order in enumerate(DOCTOR_ORDER, start=1)])
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
        st.session_state.messages.append({"role": "user", "content": user_input})
        for answer in get_response(user_input):
            st.session_state.messages.append(answer)
        st.rerun()

# ------------------------------------------------------------
# 15. 디브리핑
# ------------------------------------------------------------
if st.session_state.started:
    st.markdown('<div id="debriefing-section"></div>', unsafe_allow_html=True)

    if st.session_state.get("scroll_to_debriefing", False):
        st.session_state.scroll_to_debriefing = False
        st.components.v1.html(
            """
            <script>
            const target = window.parent.document.getElementById("debriefing-section");
            if (target) {
                target.scrollIntoView({behavior: "smooth", block: "start"});
            }
            </script>
            """,
            height=0,
        )

    st.markdown("---")
    st.subheader("🧠 디브리핑")

    if not st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        ready_for_debriefing = st.session_state.reassessment_done or st.session_state.goal_achieved
        if not ready_for_debriefing:
            st.info("중재 후 재사정과 목표달성 확인까지 진행한 후 디브리핑을 시작하는 것을 권장합니다.")
        else:
            st.success("시뮬레이션이 종료되었습니다. 아래 버튼을 눌러 디브리핑을 시작하세요.")
        if st.button("디브리핑 보기", disabled=not ready_for_debriefing):
            mark_checklist("12. 성찰: 디브리핑")
            st.session_state.ended = True
            st.session_state.show_debriefing = True
            st.session_state.scroll_to_debriefing = True
            st.rerun()

    if st.session_state.show_debriefing and not st.session_state.debrief_submitted:
        st.success("시뮬레이션이 종료되었습니다. 아래 질문을 바탕으로 먼저 성찰 답변을 작성해보세요.")
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
                st.session_state.scroll_to_debriefing = True
                st.rerun()
        with col2:
            if st.button("디브리핑 취소"):
                st.session_state.show_debriefing = False
                st.session_state.ended = False
                st.session_state.scroll_to_debriefing = True
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
