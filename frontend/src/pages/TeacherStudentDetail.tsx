import {useEffect,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {ArrowLeft,BrainCircuit,Target,TrendingUp,TriangleAlert} from 'lucide-react';
import {ResponsiveContainer,BarChart,Bar,CartesianGrid,XAxis,YAxis,Tooltip} from 'recharts';
import Layout from '../components/Layout';
import {api} from '../services/api';
import type {DashboardData} from '../types';
import {Badge,Empty,ErrorBox,Loading,pct} from '../components/UI';

export default function TeacherStudentDetail(){
  const {id}=useParams();
  const [data,setData]=useState<DashboardData>();
  const [error,setError]=useState('');

  const load=()=>{
    setError('');
    api<DashboardData>(`/api/teacher/students/${id}`)
      .then(setData)
      .catch(e=>setError(e.message));
  };

  useEffect(()=>{load();},[id]);

  if(error)return <Layout><ErrorBox message={error} retry={load}/></Layout>;
  if(!data)return <Layout><Loading label="Loading student evidence…"/></Layout>;

  const chart=data.assessments.map(x=>({
    name:x.concept_name.split(' ')[0],
    confidence:Math.round(x.average_confidence*20),
    performance:Math.round(x.performance*100)
  }));

  return <Layout>
    <div className="page-head">
      <div>
        <Link to="/teacher" className="back-link"><ArrowLeft size={16}/> Back to class</Link>
        <p className="eyebrow">STUDENT EVIDENCE</p>
        <h1>{data.user.name}</h1>
        <p>{data.user.email} · Evidence-based learning profile</p>
      </div>
    </div>

    <section className="stats">
      <article>
        <Target/>
        <label>Overall mastery</label>
        <strong>{pct(data.overall.mastery)}</strong>
        <small>Across assessed concepts</small>
      </article>
      <article>
        <BrainCircuit/>
        <label>Confidence</label>
        <strong>{pct(data.overall.confidence)}</strong>
        <small>Average reported certainty</small>
      </article>
      <article>
        <TrendingUp/>
        <label>Performance</label>
        <strong>{pct(data.overall.performance)}</strong>
        <small>Weighted demonstrated evidence</small>
      </article>
      <article>
        <TriangleAlert/>
        <label>Calibration gap</label>
        <strong className={Math.abs(data.overall.calibration_gap)>.15?'warn':''}>
          {data.overall.calibration_gap>=0?'+':''}{pct(data.overall.calibration_gap)}
        </strong>
        <small>Confidence minus performance</small>
      </article>
    </section>

    <div className="dashboard-grid">
      <section className="panel wide">
        <div className="panel-title">
          <div>
            <h2>Confidence vs performance</h2>
            <p>Calibration evidence by concept</p>
          </div>
        </div>
        {chart.length?
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" vertical={false}/>
              <XAxis dataKey="name"/>
              <YAxis domain={[0,100]}/>
              <Tooltip/>
              <Bar dataKey="confidence" fill="#94a3b8" radius={[5,5,0,0]}/>
              <Bar dataKey="performance" fill="#1d4ed8" radius={[5,5,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
          :<Empty text="This student has no assessment evidence yet."/>}
      </section>

      <section className="panel wide teacher-risk-panel">
        <h2>Active learning risks</h2>
        {data.gaps.length?
          data.gaps.map(g=>
            <div className="risk-row" key={g.id}>
              <span><TriangleAlert/></span>
              <div>
                <b>{g.concept_name}</b>
                <p>{g.gap_type.replaceAll('_',' ').toLowerCase()}</p>
              </div>
              <Badge status="AT RISK"/>
            </div>
          )
          :<Empty text="No active learning gaps detected."/>}
      </section>

      <section className="panel wide">
        <div className="panel-title">
          <div>
            <h2>Concept evidence</h2>
            <p>Current evidence for each assessed concept</p>
          </div>
        </div>

        {data.assessments.length?
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Concept</th>
                  <th>Mastery</th>
                  <th>Confidence</th>
                  <th>Performance</th>
                  <th>Recall</th>
                  <th>Transfer</th>
                  <th>Calibration</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {data.assessments.map(a=>
                  <tr key={a.concept_id}>
                    <td><b>{a.concept_name}</b></td>
                    <td>{pct(a.concept_mastery)}</td>
                    <td>{pct(a.average_confidence/5)}</td>
                    <td>{pct(a.performance)}</td>
                    <td>{pct(a.recall_score)}</td>
                    <td>{pct(a.transfer_score)}</td>
                    <td>{a.calibration_gap>=0?'+':''}{pct(a.calibration_gap)}</td>
                    <td><Badge status={a.risk_level}/></td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          :<Empty text="No concept evidence available yet."/>}
      </section>
    </div>
  </Layout>;
}
