import {useEffect,useState} from 'react';
import {Send,Sparkles} from 'lucide-react';
import {useSearchParams} from 'react-router-dom';
import Layout from '../components/Layout';
import {api} from '../services/api';
import type {DashboardData} from '../types';

type Message={who:'ai'|'you';text:string};
type TutorReply={message:string;action:string;is_complete:boolean;provider_mode:'real'|'demo'};
const welcome:Message={who:'ai',text:'Explain what you currently think happens and why. I will ask one question at a time before giving an explanation.'};

export default function Tutor(){
 const [params]=useSearchParams();const requestedConcept=Number(params.get('concept_id'))||0;
 const [messages,setMessages]=useState<Message[]>([welcome]);const [text,setText]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [conceptId,setConceptId]=useState(requestedConcept||1);const [concept,setConcept]=useState('your current concept');const [mode,setMode]=useState<'real'|'demo'>();
 useEffect(()=>{api<DashboardData>('/api/student/dashboard').then(d=>{const target=(requestedConcept&&[...d.gaps,...d.assessments].find(item=>item.concept_id===requestedConcept))||d.gaps[0]||d.assessments[0];if(target){setConceptId(target.concept_id);setConcept('concept_name' in target?target.concept_name:'your current concept')}}).catch(()=>{})},[requestedConcept]);
 async function send(e:React.FormEvent){e.preventDefault();const value=text.trim();if(!value||busy)return;const prior=[...messages,{who:'you' as const,text:value}];setMessages(prior);setText('');setBusy(true);setError('');try{const history=prior.slice(1).map(m=>({role:m.who==='ai'?'tutor':'student',content:m.text}));const r=await api<TutorReply>('/api/ai/tutor',{method:'POST',body:JSON.stringify({concept_id:conceptId,message:value,history})});setMessages(m=>[...m,{who:'ai',text:r.message}]);setMode(r.provider_mode)}catch(e){setError(e instanceof Error?e.message:'The tutor could not respond.')}finally{setBusy(false)}}
 return <Layout><div className="tutor"><header><span><Sparkles/></span><div><p className="eyebrow">SOCRATIC SUPPORT</p><h1>AI Tutor</h1><p>Adaptive guidance for {concept}. {mode&&<small aria-label="AI provider mode">{mode==='real'?'Real AI connected':'Demo mode'}</small>}</p></div></header><div className="chat" aria-live="polite">{messages.map((m,i)=><div className={`message ${m.who}`} key={i}><small>{m.who==='ai'?'CALIBRATE AI':'YOU'}</small><p>{m.text}</p></div>)}{busy&&<div className="message ai"><p>AI Tutor is considering your reasoning…</p></div>}</div>{error&&<p role="alert" className="error">{error}</p>}<form onSubmit={send}><label htmlFor="tutor-input">Your reasoning</label><textarea id="tutor-input" value={text} onChange={e=>setText(e.target.value)} placeholder="Explain what you think happens and why…"/><button className="button" disabled={busy||!text.trim()}>Send <Send/></button></form></div></Layout>
}
