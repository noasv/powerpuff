import type {User} from '../types';const base=import.meta.env.VITE_API_URL||'';
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{const token=localStorage.getItem('token');const r=await fetch(base+path,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{ }),...options.headers}});if(!r.ok){let m='Request failed';try{m=(await r.json()).detail||m}catch{}throw new Error(m)}if(r.status===204)return undefined as T;return r.json()}
export function saveAuth(v:{access_token:string;user:User}){localStorage.setItem('token',v.access_token);localStorage.setItem('user',JSON.stringify(v.user))}
export function user():User|null{try{return JSON.parse(localStorage.getItem('user')||'null')}catch{return null}}
export function logout(){localStorage.clear()}
