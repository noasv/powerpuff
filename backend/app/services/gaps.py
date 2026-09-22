def detect(accuracy,confidence,recall,transfer,explanation):
 gaps=[]; perf=.35*accuracy+.25*recall+.25*transfer+.15*explanation
 evidence={"confidence":confidence,"recognition":accuracy,"recall":recall,"transfer":transfer,"explanation":explanation}
 if accuracy>=.7 and recall<.55:gaps.append(('RECOGNITION_WITHOUT_RECALL',.8,evidence,'Practice free recall before reviewing choices.'))
 if confidence>=.8 and perf<=.55:gaps.append(('OVERCONFIDENCE',min(1,confidence-perf),evidence,'Predict, explain, then verify in a new context.'))
 if accuracy>=.8 and transfer<=.55:gaps.append(('TRANSFER_FAILURE',.75,evidence,'Practice changed-condition and boundary cases.'))
 if accuracy>=.7 and recall<.65 and transfer<.55:gaps.append(('FRAGILE_MENTAL_MODEL',.85,evidence,'Rebuild the causal model with the AI Tutor.'))
 return gaps
