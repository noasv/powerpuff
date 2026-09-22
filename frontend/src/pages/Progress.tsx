import {useEffect,useState} from 'react';
import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import Layout from '../components/Layout';
import {Badge,Empty,ErrorBox,Loading,pct} from '../components/UI';
import {api} from '../services/api';
import type {ProgressData} from '../types';

const colors=['#1d4ed8','#7c3aed','#059669','#d97706','#dc2626','#0891b2'];
const stamp=(value:string)=>new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});

export default function Progress(){
 const [data,setData]=useState<ProgressData>();const [error,setError]=useState('');
 const load=()=>api<ProgressData>('/api/student/progress').then(setData).catch(e=>setError(e.message));
 useEffect(()=>{load()},[]);
 if(error)return <Layout><ErrorBox message={error} retry={load}/></Layout>;
 if(!data)return <Layout><Loading label="Loading your learning history…"/></Layout>;
 const concepts=[...new Map(data.history.map(point=>[point.concept_id,point.concept_name])).entries()];
 const chart=data.history.map(point=>({label:stamp(point.created_at),[`concept_${point.concept_id}`]:Math.round(point.concept_mastery*100)}));
 return <Layout><div className="page-head"><div><p className="eyebrow">LEARNING HISTORY</p><h1>Progress</h1><p>How your demonstrated understanding has changed with new evidence.</p></div></div>
  <section className="panel progress-history"><div className="panel-title"><div><h2>Mastery progress</h2><p>Each point is a real assessment or Tutor verification event.</p></div></div>
   {chart.length?<ResponsiveContainer width="100%" height={300}><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="label"/><YAxis domain={[0,100]} unit="%"/><Tooltip/><Legend/>{concepts.map(([id,name],index)=><Line key={id} connectNulls type="monotone" dataKey={`concept_${id}`} name={name} stroke={colors[index%colors.length]} strokeWidth={3}/>)}</LineChart></ResponsiveContainer>:<Empty text="Complete a diagnostic to begin your progress history."/>}
  </section>
  <section className="panel table-panel"><h2>Evidence timeline</h2><p>Earlier evidence remains visible after your profile improves.</p>{data.history.length?<div className="table-wrap"><table><thead><tr><th>When</th><th>Concept</th><th>Evidence</th><th>Mastery</th><th>Recall</th><th>Transfer</th><th>Status</th></tr></thead><tbody>{data.history.map(point=><tr key={point.attempt_id}><td>{stamp(point.created_at)}</td><td>{point.concept_name}</td><td>{point.source==='tutor_verification'?'Tutor verification':point.question_type.replaceAll('_',' ').toLowerCase()}</td><td>{pct(point.concept_mastery)}</td><td>{pct(point.recall_score)}</td><td>{pct(point.transfer_score)}</td><td><Badge status={point.risk_level}/></td></tr>)}</tbody></table></div>:<Empty text="No learning evidence yet."/>}</section>
  <section className="panel table-panel"><h2>Gap history</h2><p>Resolved findings remain inspectable and are not treated as current risks.</p>{data.gaps.length?<div className="table-wrap"><table><thead><tr><th>Observed</th><th>Concept</th><th>Finding</th><th>Severity</th><th>Status</th></tr></thead><tbody>{data.gaps.map(gap=><tr key={gap.id}><td>{gap.created_at&&stamp(gap.created_at)}</td><td>{gap.concept_name}</td><td>{gap.gap_type.replaceAll('_',' ').toLowerCase()}</td><td>{pct(gap.severity)}</td><td><Badge status={gap.resolved_at?'RESOLVED':'ACTIVE'}/></td></tr>)}</tbody></table></div>:<Empty text="No concept gaps have been observed."/>}</section>
 </Layout>
}
