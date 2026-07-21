
from __future__ import annotations
import logging
import random
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
try:
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
except ImportError:
 import simple_plot as plt
from adaptive_tlbo import AdaptiveTLBO
from dataset import Dataset
from fitness import Fitness
from constraint_checker import ConstraintChecker
from excel_formatter import ExcelFormatter
from config import (EARLY_STOPPING_ROUNDS, ENABLE_PLOTS, ENABLE_VERBOSE,
                    IMPROVEMENT_THRESHOLD, ITERATIONS, OUTPUT_DIR, PLOT_DPI,
                    POPULATION, RANDOM_SEED, RESULTS_DIR, RUNS)
from logging_utils import configure_logging

ROOT = Path(__file__).resolve().parents[1]
RESULTS = RESULTS_DIR
OUTPUT = OUTPUT_DIR
LOGGER = logging.getLogger("adaptive_tlbo")
EXPERIMENTS=[("Base TLBO",dict(use_dynamic_priority=False,use_faculty_satisfaction=False,use_adaptive_parameters=False,use_conflict_prediction=False)),("TLBO + Dynamic Priority",dict(use_dynamic_priority=True,use_faculty_satisfaction=False,use_adaptive_parameters=False,use_conflict_prediction=False)),("TLBO + Dynamic Priority + Faculty Satisfaction",dict(use_dynamic_priority=True,use_faculty_satisfaction=True,use_adaptive_parameters=False,use_conflict_prediction=False)),("Complete Adaptive TLBO",dict(use_dynamic_priority=True,use_faculty_satisfaction=True,use_adaptive_parameters=True,use_conflict_prediction=True))]
COLORS=["#8C8C8C","#4E79A7","#59A14F","#E15759"]

def run(ds, name, opts, seed):
    random.seed(seed)

    run_number = (seed - RANDOM_SEED) % RUNS + 1

    LOGGER.info("Starting %s, run %d/%d", name, run_number, RUNS)

    start = time.perf_counter()

    optimizer = AdaptiveTLBO(
        ds,
        population_size=POPULATION,
        iterations=ITERATIONS,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        improvement_threshold=IMPROVEMENT_THRESHOLD,
        random_seed=seed,
        verbose=ENABLE_VERBOSE,
        **opts
    )

    timetable, best_fitness, history = optimizer.optimize()

    execution_time = time.perf_counter() - start

    fitness = Fitness(ds)

    conflicts = fitness.constraint_checker.detailed_conflicts(
        timetable,
        ds
    )

    row = {
        "Experiment": name,
        "Run": run_number,
        "Seed": seed,
        "Fitness": best_fitness,
        "FacultySatisfaction": fitness.faculty_satisfaction.calculate(timetable),
        "Conflicts": sum(conflicts.values()),
        "ConstraintViolationScore": sum(conflicts.values()),
        "ExecutionTimeSeconds": execution_time,
        "IterationsCompleted": optimizer.completed_iterations,
    }

    history = pd.DataFrame(history)

    return timetable, history, row

def plot(summary, hist, runs):
    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    for index, (name, group) in enumerate(hist.groupby("Experiment", sort=False)):
        curve = group.groupby("Iteration")["BestFitness"].mean()
        axis.plot(curve.index, curve.values, linewidth=2, color=COLORS[index], label=name)
    axis.set(xlabel="Iteration", ylabel="Mean best fitness", title="Convergence comparison", xlim=(1, ITERATIONS)); axis.legend(fontsize=8)
    figure.savefig(RESULTS / "convergence_comparison.png", dpi=PLOT_DPI); plt.close(figure)
    figure, axis = plt.subplots(figsize=(7.5, 4.5), constrained_layout=True)
    complete = hist[hist["Experiment"] == "Complete Adaptive TLBO"]
    for _, group in complete.groupby("Run"):
        axis.plot(group["Iteration"], group["BestFitness"], color=COLORS[-1], alpha=.15)
    curve = complete.groupby("Iteration")["BestFitness"].mean(); axis.plot(curve.index, curve.values, color="#A61C1C", linewidth=2.5, label="Mean of 10 runs")
    axis.set(xlabel="Iteration", ylabel="Best fitness", title="Convergence of Complete Adaptive TLBO", xlim=(1, ITERATIONS)); axis.legend()
    figure.savefig(RESULTS / "convergence_plot.png", dpi=PLOT_DPI); plt.close(figure)
    for column, filename, title, label in [("Mean Fitness", "ablation_comparison.png", "Ablation comparison", "Mean fitness"), ("Average Time", "execution_time_comparison.png", "Execution time comparison", "Seconds"), ("Average Faculty Satisfaction", "faculty_satisfaction_comparison.png", "Faculty satisfaction comparison", "Satisfaction (%)")]:
        figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True); axis.bar(summary["Experiment"], summary[column], color=COLORS); axis.set(ylabel=label, title=title); axis.tick_params(axis="x", rotation=14); figure.savefig(RESULTS / filename, dpi=PLOT_DPI); plt.close(figure)
    figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True); axis.boxplot([group["Fitness"] for _, group in runs.groupby("Experiment", sort=False)], tick_labels=summary["Experiment"], showmeans=True); axis.set(ylabel="Fitness", title="Fitness distribution"); axis.tick_params(axis="x", rotation=14); figure.savefig(RESULTS / "fitness_boxplot.png", dpi=PLOT_DPI); plt.close(figure)
def reports(ds,tt,perf,summary):
 f=Fitness(ds); cc=ConstraintChecker(); detail=cc.detailed_conflicts(tt,ds)
 pd.DataFrame([{"Faculty":x,"Scheduled Periods":sum(e["Faculty"]==x for e in tt),"Maximum Daily Load":ds.faculty_daily_limits.get(x,3)} for x in ds.get_faculty().FacultyName.unique()]).to_csv(RESULTS/"faculty_workload_report.csv",index=False);pd.DataFrame([{"Faculty":x,"Scheduled Periods":sum(e["Faculty"]==x for e in tt),"Maximum Daily Load":ds.faculty_daily_limits.get(x,3)} for x in ds.get_faculty().FacultyName.unique()]).to_csv(RESULTS/"Faculty_Workload.csv",index=False)
 pd.DataFrame([{"Room":x,"Scheduled Periods":sum(e["Room"]==x for e in tt),"Available Weekly Periods":len(ds.get_days())*len(ds.get_periods())} for x in ds.get_rooms().RoomID]).to_csv(RESULTS/"classroom_utilization_report.csv",index=False);pd.DataFrame([{"Room":x,"Scheduled Periods":sum(e["Room"]==x for e in tt),"Available Weekly Periods":len(ds.get_days())*len(ds.get_periods())} for x in ds.get_rooms().RoomID]).to_csv(RESULTS/"Room_Utilization.csv",index=False)
 pd.DataFrame([{"Faculty":x,"Satisfaction (%)":f.faculty_satisfaction.calculate([e for e in tt if e["Faculty"]==x])} for x in ds.get_faculty().FacultyName.unique()]).to_csv(RESULTS/"faculty_satisfaction_report.csv",index=False)
 pd.DataFrame(detail.items(),columns=["Constraint","Violations"]).to_csv(RESULTS/"constraint_violation_report.csv",index=False);pd.DataFrame(detail.items(),columns=["Constraint","Violations"]).to_csv(RESULTS/"Constraint_Report.csv",index=False);pd.DataFrame([perf]).to_csv(RESULTS/"optimization_summary_report.csv",index=False)
 try:
  from reportlab.lib.pagesizes import A4,landscape
  from reportlab.lib import colors
  from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
  from reportlab.lib.styles import getSampleStyleSheet
  style=getSampleStyleSheet(); data=[list(summary.columns)]+summary.round(3).astype(str).values.tolist();tab=Table(data,repeatRows=1);tab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17365D")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),7)]));SimpleDocTemplate(str(RESULTS/"Experimental_Results_Report.pdf"),pagesize=landscape(A4)).build([Paragraph("Experimental Results Report",style["Title"]),Paragraph("Adaptive TLBO: 10 independently seeded runs per configuration.",style["BodyText"]),Spacer(1,10),tab])
 except ImportError: pass
def main():
 configure_logging(ENABLE_VERBOSE)
 RESULTS.mkdir(exist_ok=True);OUTPUT.mkdir(exist_ok=True);ds=Dataset();ds.load_data();rows=[];hs=[];best=None
 for i,(n,opt) in enumerate(EXPERIMENTS):
  for r in range(RUNS):
   tt,h,row=run(ds,n,opt,RANDOM_SEED+i*100+r);rows.append(row);h.insert(0,"Run",r+1);h.insert(0,"Seed",row["Seed"]);h.insert(0,"Experiment",n);hs.append(h)
   if n=="Complete Adaptive TLBO" and (best is None or row["Fitness"]>best[2]["Fitness"]):best=(tt,h,row)
 runs=pd.DataFrame(rows);hist=pd.concat(hs,ignore_index=True);summary=runs.groupby("Experiment",sort=False).agg(**{"Mean Fitness":("Fitness","mean"),"Median Fitness":("Fitness","median"),"Std Dev":("Fitness","std"),"Variance":("Fitness","var"),"Best Fitness":("Fitness","max"),"Worst Fitness":("Fitness","min"),"Average Time":("ExecutionTimeSeconds","mean"),"Average Faculty Satisfaction":("FacultySatisfaction","mean"),"Average Conflicts":("Conflicts","mean"),"Average Constraint Violation Score":("ConstraintViolationScore","mean")}).reset_index();summary["Improvement over Base TLBO (%)"]=(summary["Mean Fitness"]/summary.loc[0,"Mean Fitness"]-1)*100;tt=best[0]; cols=["Section","Course","Faculty","Room","Day","Time","Period","Hours","Priority","SubjectID","Type"];df=pd.DataFrame(tt)[cols]
 runs.to_csv(RESULTS/"ablation_results.csv",index=False);summary.to_csv(RESULTS/"statistical_analysis.csv",index=False);hist.to_csv(RESULTS/"fitness_history.csv",index=False);hist[hist.Experiment=="Complete Adaptive TLBO"].to_csv(RESULTS/"iteration_results.csv",index=False);df.to_csv(RESULTS/"final_timetable.csv",index=False);df.to_csv(RESULTS/"optimized_timetable.csv",index=False)
 perf={"Experiment":"Complete Adaptive TLBO","Best Fitness":best[2]["Fitness"],"Faculty Satisfaction":best[2]["FacultySatisfaction"],"Conflicts":best[2]["Conflicts"],"Constraint Violation Score":best[2]["ConstraintViolationScore"],"GeneratedAt":datetime.now().isoformat(timespec="seconds")};pd.DataFrame([perf]).to_csv(RESULTS/"performance_metrics.csv",index=False);(plot(summary,hist,runs) if ENABLE_PLOTS else None);reports(ds,tt,perf,summary);ExcelFormatter(ds).save(tt,perf,summary.iloc[-1].to_dict(),RESULTS/"University_Timetable.xlsx")
 try:
  from reportlab.lib.pagesizes import A4,landscape
  from reportlab.platypus import SimpleDocTemplate,Paragraph
  from reportlab.lib.styles import getSampleStyleSheet
  SimpleDocTemplate(str(RESULTS/"University_Timetable.pdf"),pagesize=landscape(A4)).build([Paragraph("University Timetable",getSampleStyleSheet()["Title"]),Paragraph("Professional timetable data is available in University_Timetable.xlsx.",getSampleStyleSheet()["BodyText"])])
 except ImportError:pass
 LOGGER.info("Completed %d independent runs in %s", len(rows), RESULTS)
 print("\nAll reports generated successfully.")
 print(f"Results saved in: {RESULTS}")

if __name__=="__main__":main()


