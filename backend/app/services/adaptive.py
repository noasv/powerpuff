def next_action(correct:bool,confidence:int,recall:float|None=None,transfer:float|None=None):
 high=confidence>=4
 if not correct:return 'CONFLICT' if high else 'FOUNDATION'
 if high and recall is not None and recall<.6:return 'RECALL'
 if high and transfer is not None and transfer<.6:return 'CONFLICT'
 if confidence<=2:return 'VERIFY'
 if transfer is not None and transfer>=.7:return 'INCREASE_DIFFICULTY'
 return 'RECALL'
