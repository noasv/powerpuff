from .provider import AIProvider
class MockAIProvider(AIProvider):
 async def generate(self,kind,p):
  if kind=='analysis':
   text=(p.get('explanation') or '').lower(); terms=sum(x in text for x in ['because','therefore','force','mass','acceleration','relationship']); score=min(.95,.25+terms*.11+min(len(text),240)/800)
   return {'concept_understanding':score,'causal_reasoning':max(.2,score-.08),'use_of_terms':score,'logical_consistency':score,'memorized_language':max(0,.7-score),'misconceptions':[] if score>.6 else ['Relationship is stated without a causal explanation'],'missing_components':[] if score>.7 else ['Explain how changing one variable affects another'],'overall_score':round(score,2)}
  if kind=='conflict': return {'question':'A student says doubling mass while force stays constant doubles acceleration. Find and explain the mistake.','type':'CONFLICT','concept_id':p['concept_id'],'difficulty':.72,'correct_answer':'Acceleration halves because a = F/m.','explanation':'With constant force, acceleration is inversely proportional to mass.','trap_type':'CHANGED_CONDITIONS'}
  if kind=='question': return {'question':'Without a formula list, describe the causal relationship in this concept.','type':'RECALL','concept_id':p['concept_id'],'difficulty':p.get('difficulty',.5),'correct_answer':'A complete causal relationship','explanation':'Recall requires producing the relationship without choices.','trap_type':None}
  text=p.get('latest_response','').lower(); prior=p.get('previous_tutor_turns',[]); last_action=prior[-1]['action'] if prior else ''
  misconception='Confuses which quantity is held constant' if any(x in text for x in ('always','regardless','stays the same')) else 'States a rule without explaining the causal relationship'
  strong=any(x in text for x in ('because','therefore','depends on','causes')) and len(text.split())>=8
  if last_action=='verify':
   return {'message':('Your verification reasoning connects the changed condition to the outcome. You have demonstrated improved understanding.' if strong else 'Which changed condition in the new problem affects your result, and why?'),'action':'evaluate_verification','identified_gap':'' if strong else misconception,'misconception':'' if strong else misconception,'hint_level':0 if strong else 1,'reasoning_quality':'strong' if strong else 'developing','should_reveal_explanation':False,'is_complete':strong,'verification_task':None,'provider_mode':'demo'}
  if strong:
   task=f"New case: change one important condition in {p.get('concept','this concept')}. Predict the outcome and justify why it changes."
   return {'message':task,'action':'verify','identified_gap':'Transfer has not yet been demonstrated','misconception':'','hint_level':0,'reasoning_quality':'strong','should_reveal_explanation':False,'is_complete':False,'verification_task':task,'provider_mode':'demo'}
  if 'double' in text or 'increase' in text:
   message='What did you assume stays constant when that quantity changes, and how does that affect the relationship?';action='question'
  elif len(text.split())<5:
   message='What relationship between the two main quantities are you using, and why?';action='diagnose'
  else:
   message='Consider changing only one quantity while holding the other condition fixed. What would your rule predict, and does that prediction make sense?';action='counterexample'
  return {'message':message,'action':action,'identified_gap':misconception,'misconception':misconception,'hint_level':0,'reasoning_quality':'weak' if len(text.split())<5 else 'developing','should_reveal_explanation':False,'is_complete':False,'verification_task':None,'provider_mode':'demo'}
