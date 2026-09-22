from ..config.scoring import PERFORMANCE_WEIGHTS as P,MASTERY_WEIGHTS as M
def performance(accuracy,recall,transfer,explanation):
 """Combine concept evidence without rounding before presentation."""
 return P['accuracy']*accuracy+P['recall']*recall+P['transfer']*transfer+P['explanation']*explanation
def confidence_score(confidence):
 """Normalize stored 1--5 mean confidence to the 0--1 metric scale."""
 return confidence/5
def calibration_gap(confidence,score):
 """Signed confidence minus performance for the same concept evidence."""
 return confidence_score(confidence)-score
def mastery(accuracy,recall,transfer,explanation,gap,historical=None):
 quality=max(0,1-abs(gap)); current=M['accuracy']*accuracy+M['recall']*recall+M['transfer']*transfer+M['explanation']*explanation+M['calibration']*quality
 return round((.8*current+.2*historical) if historical is not None else current,4)
def risk(master,accuracy,recall,transfer):
 if master>=.8 and recall>=.7 and transfer>=.7:return 'MASTERED'
 if master>=.65:return 'STABLE'
 if accuracy>=.65 and (recall<.6 or transfer<.6):return 'FRAGILE'
 return 'AT RISK'
