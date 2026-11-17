"""Gol attesi · FASE 1 (audit, 17/11/2026, richiesta di Denny): bias, fasce di gol, dispersione, correlazione casa-ospite, pendenza,
elasticità al livello del campionato e rho Dixon-Coles sulle previsioni walk-forward dell app (ricerca/base, dal 2023). Nessuna modifica al modello.
Uso: python tools/audit_gol.py (dalla cartella del progetto, con ricerca/ scaricata da tools/ricerca_locale.sh)"""
import json,glob,os,numpy as np
from scipy.stats import poisson
R=[]
for f in glob.glob("ricerca/base/*.json"):
    lg=os.path.basename(f)[:-5]
    for m in json.load(open(f)):
        g=m.get("g"); y=(m.get("y") or {}).get("g")
        if not g or not y or y[0] is None or g[0] is None: continue
        R.append((lg,m["d"],g[0],g[1],y[0],y[1]))
import pandas as pd
D=pd.DataFrame(R,columns="lg d lh la yh ya".split())
D["per"]=np.where(D.d<="2024-06-30","scelta",np.where(D.d<="2025-06-30","verifica","holdout"))
D["lt"]=D.lh+D.la; D["yt"]=D.yh+D.ya; D=D.rename(columns={"lt":"tl","yt":"ty"})
print("partite",len(D), D.d.min(), D.d.max())
for p,G in D.groupby("per",sort=False):
    print(f"\n== {p} ({len(G)})")
    print(f" media prevista casa {G.lh.mean():.3f} reale {G.yh.mean():.3f} | ospite {G.la.mean():.3f} reale {G.ya.mean():.3f} | totale {G.tl.mean():.3f} reale {G.ty.mean():.3f}")
    print(f" MAE totale {np.abs(G.ty-G.tl).mean():.3f} (costante media lega-periodo: {np.abs(G.ty-G.groupby('lg').ty.transform('mean')).mean():.3f}) RMSE {np.sqrt(((G.ty-G.tl)**2).mean()):.3f}")
    # dispersione: var(y-l)/l
    print(f" dispersione casa {((G.yh-G.lh)**2).mean()/G.lh.mean():.3f} ospite {((G.ya-G.la)**2).mean()/G.la.mean():.3f} totale {((G.ty-G.tl)**2).mean()/G.tl.mean():.3f} (Poisson = 1)")
    print(f" correlazione residui casa-ospite {np.corrcoef(G.yh-G.lh,G.ya-G.la)[0,1]:+.3f}")
    # fasce totale
    for lab,lo,hi in (("0-1",0,1),("2",2,2),("3",3,3),("4+",4,99),("5+",5,99),("3+",3,99)):
        pp=poisson.cdf(hi,G.tl)-poisson.cdf(lo-1,G.tl)
        print(f"  totale {lab:3}: prevista {pp.mean()*100:5.1f}  reale {((G.ty>=lo)&(G.ty<=hi)).mean()*100:5.1f}")
    # 1X2 indip poisson
    def p1x2(lh,la):
        k=np.arange(11); ph=poisson.pmf(k[None,:],lh[:,None]); pa=poisson.pmf(k[None,:],la[:,None])
        M=ph[:,:,None]*pa[:,None,:]; return np.tril(M,-1).sum((1,2)), np.trace(M,axis1=1,axis2=2), np.triu(M,1).sum((1,2))
    a,b,c=p1x2(G.lh.values,G.la.values)
    print(f"  1X2 prevista {a.mean()*100:.1f}/{b.mean()*100:.1f}/{c.mean()*100:.1f} reale {(G.yh>G.ya).mean()*100:.1f}/{(G.yh==G.ya).mean()*100:.1f}/{(G.yh<G.ya).mean()*100:.1f}")
    # se la media fosse giusta (lambda riscalato al reale del periodo), resta lo scarto?
    k=G.ty.mean()/G.tl.mean(); pp=1-poisson.cdf(2,G.tl*k)
    print(f"  3+ con lambda riscalato ×{k:.3f}: prevista {pp.mean()*100:.1f} reale {(G.ty>=3).mean()*100:.1f}")
    # calibrazione per decili di lt
    G=G.assign(q=pd.qcut(G.tl,5,labels=False))
    print("  per quinti di gol attesi: " + " | ".join(f"{x.tl.mean():.2f}→{x.ty.mean():.2f} 3+ {(1-poisson.cdf(2,x.tl)).mean()*100:.0f}/{(x.ty>=3).mean()*100:.0f}" for _,x in G.groupby("q")))
H=D[D.per=="holdout"]
print("\nholdout per campionato (reale − previsto, gol totali; 3+ prevista/reale):")
out=[]
for lg,G in H.groupby("lg"):
    out.append((G.ty.mean()-G.tl.mean(),lg,len(G),(1-poisson.cdf(2,G.tl)).mean()*100,(G.ty>=3).mean()*100))
for o in sorted(out): print(f"  {o[1]:4} n={o[2]:4} {o[0]:+.2f}  3+ {o[3]:.0f}/{o[4]:.0f}")
# andamento mensile scarto
D["mese"]=D.d.str[:7]
print("\nscarto mensile (reale−previsto, totale):"," ".join(f"{m[2:]}:{(x.ty.mean()-x.tl.mean()):+.2f}" for m,x in D.groupby("mese")))
print("\n=== pendenza: reale = a + b·previsto (per squadra) e elasticità al livello del campionato")
from scipy.optimize import minimize
for p,G in D.groupby("per",sort=False):
    y=np.r_[G.yh,G.ya]; l=np.r_[G.lh,G.la]
    x=np.log(l); f=lambda b: (np.exp(b[0]+b[1]*x)-y*(b[0]+b[1]*x)).sum(); bb=minimize(f,[0,1]).x
    mu=np.exp(bb[0]+bb[1]*x); I=np.array([[mu.sum(),(mu*x).sum()],[(mu*x).sum(),(mu*x*x).sum()]]); se=np.sqrt(np.linalg.inv(I)[1,1])
    class _M: pass
    m=_M(); m.params=bb; m.bse=[0,se]
    S=G.groupby("lg").agg(t=("tl","mean"),y=("ty","mean"))
    e=np.polyfit(np.log(S.t),np.log(S.y),1)[0]
    print(f" {p}: log(gol reali) su log(λ): pendenza {m.params[1]:.3f} ± {m.bse[1]:.3f} · campionati: log(reale medio) su log(previsto medio) pendenza {e:.2f}")
    # log-loss risultato esatto vs baseline media lega-periodo (indip poisson)
    def ll(lh,la,yh,ya): return -(poisson.logpmf(yh,lh)+poisson.logpmf(ya,la)).mean()
    mh=G.groupby("lg").yh.transform("mean"); ma=G.groupby("lg").ya.transform("mean")
    print(f"   log-loss gol (casa+ospite): modello {ll(G.lh,G.la,G.yh,G.ya):.4f} · medie di lega del periodo (con il senno di poi) {ll(mh,ma,G.yh,G.ya):.4f}")
    # pareggi per lambda simili
    from scipy.optimize import minimize_scalar
    def nll(r):
        lh,la,yh,ya=G.lh.values,G.la.values,G.yh.values,G.ya.values
        t=np.ones(len(G)); t[(yh==0)&(ya==0)]=1-lh[(yh==0)&(ya==0)]*la[(yh==0)&(ya==0)]*r; t[(yh==0)&(ya==1)]=1+lh[(yh==0)&(ya==1)]*r; t[(yh==1)&(ya==0)]=1+la[(yh==1)&(ya==0)]*r; t[(yh==1)&(ya==1)]=1-r
        return -np.log(np.maximum(t,1e-9)).sum()
    print(f"   rho Dixon-Coles di massima verosimiglianza (λ dell'app): {minimize_scalar(nll,bounds=(-0.3,0.3),method='bounded').x:+.3f}")
