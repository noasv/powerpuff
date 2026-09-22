export interface User{id:number;name:string;email:string;role:'student'|'teacher'|'admin'}
export interface Subject{id:number;name:string;description:string}
export interface Concept{id:number;subject_id:number;name:string;description:string;difficulty:number;prerequisite_ids:number[]}
export interface Question{id:number;concept_id:number;type:string;difficulty:number;question_text:string;metadata:{options?:string[]};why:string}
export interface Assessment{concept_id:number;concept_name:string;accuracy:number;average_confidence:number;recall_score:number;transfer_score:number;explanation_score:number;performance_score:number;calibration_gap:number;concept_mastery:number;risk_level:string;updated_at:string}
export interface Gap{id:number;concept_id:number;concept_name:string;gap_type:string;severity:number;evidence:Record<string,number>;recommended_action:string;created_at?:string;resolved_at?:string|null}
export interface ProgressPoint extends Omit<Assessment,'updated_at'>{attempt_id:number;question_type:string;source:'assessment'|'tutor_verification';created_at:string}
export interface ProgressData{history:ProgressPoint[];gaps:Gap[]}
export interface Recommendation{concept_id:number|null;concept_name:string|null;subject_name:string|null;gap_id:number|null;destination:'tutor'|'assessment';recommended_action:string;reason:string;priority_score:number}
export interface DashboardData{user:User;overall:{confidence:number;performance:number;calibration_gap:number;mastery:number};assessments:Assessment[];gaps:Gap[];recommendation:Recommendation}
