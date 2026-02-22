from fastapi import APIRouter
from pydantic import BaseModel

class EvaluationData(BaseModel):
    job_fit_score: int
    predictive_success_score: int

class CompareScoringResponse(BaseModel):
    accuracy: int
    label: str 
    recommendation: str

router = APIRouter(prefix="/reports", tags=["Accuracy Reports"])


# another endpoint for the history of accuracy or average accuracy can be created, but will need database operations


# compares the AI's results to the HR's own results regarding a candidate's scoring
@router.post("/compare")
async def compare_scoring(ai_evaluation_data: EvaluationData, hr_evaluation_data: EvaluationData) -> CompareScoringResponse:
    MAX_SCORE = 100

    # calculate similarity between AI and HR's job fit score
    job_fit_score = 1 - (
        abs(ai_evaluation_data.job_fit_score - hr_evaluation_data.job_fit_score)
        / MAX_SCORE
    )
    # calculate similarity between AI and HR's skills gaps recommendation score
    pred_success_score = 1 - (
        abs(ai_evaluation_data.predictive_success_score - hr_evaluation_data.predictive_success_score)
        / MAX_SCORE
    )

    overall_score = (job_fit_score + pred_success_score) / 2 # equal weights, 50/50
    ai_accuracy_pct = int(overall_score * 100)

    # determine the label based on the percentage
    if ai_accuracy_pct >= 90:
        label = "Very high accuracy"
        recommendation = "The AI highly matches with the HR's decision."
    elif ai_accuracy_pct >= 80:
        label = "High accuracy"
        recommendation = "The AI matches with the HR's decision well, but consider changing the weight percentages of the scoring."
    elif ai_accuracy_pct >= 70:
        label = "Moderate accuracy"
        recommendation = "The AI generally matches with the HR's decision, but it is recommended to make changes to the weight percentages of the scoring."
    else:
        label = "Low accuracy"
        recommendation = "The AI's decision does not match well with the HR's decision. It might be a human error or the weights of the scoring need to be adjusted."
    
    return CompareScoringResponse(
        accuracy=ai_accuracy_pct,
        label=label,
        recommendation=recommendation
    )






