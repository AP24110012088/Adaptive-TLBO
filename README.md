# Adaptive TLBO Framework with Dynamic Priority Adjustment and Faculty Satisfaction Evaluation for Academic Timetable Scheduling

A conference-ready implementation of an **Adaptive Teaching–Learning-Based Optimization (Adaptive TLBO)** framework for automatic academic timetable scheduling. The proposed framework integrates **Dynamic Priority Adjustment** and **Faculty Satisfaction Evaluation** to generate high-quality, conflict-free academic timetables while improving resource utilization, workload balance, and faculty satisfaction.

---

## Project Overview

Academic timetable scheduling is a complex optimization problem that involves assigning faculty members, subjects, classrooms, and time slots while satisfying numerous institutional constraints.

This project extends the conventional Teaching–Learning-Based Optimization (TLBO) algorithm by incorporating adaptive optimization strategies that improve convergence and timetable quality. The framework dynamically adjusts scheduling priorities, evaluates faculty satisfaction, preserves high-quality solutions, and applies local search to refine promising timetables.

---

## Features

- Adaptive Teaching–Learning-Based Optimization (Adaptive TLBO)
- Dynamic Priority Adjustment
- Faculty Satisfaction Evaluation
- Elite Preservation
- Adaptive Teaching and Learning Factors
- Local Search Refinement
- Conflict-Free Timetable Generation
- Automatic Constraint Validation
- Performance Evaluation
- Convergence Analysis
- Ablation Study
- Professional University Timetable Generation

---

## Project Structure

```
Adaptive_TLBO_Conference_Ready/
│
├── data/
│   ├── faculty.csv
│   ├── rooms.csv
│   ├── subjects.csv
│   └── timeslots.csv
│
├── diagrams/
│
├── logs/
│
├── output/
│
├── report/
│
├── results/
│
├── src/
│
├── README.md
└── requirements.txt
```

---

## Installation

Install the required packages.

```bash
pip install -r requirements.txt
```

---

## Running the Project

```bash
cd src
python main.py
```

---

## Output

The framework automatically generates:

- Optimized university timetable
- Fitness history
- Convergence plots
- Ablation study results
- Faculty satisfaction report
- Classroom utilization report
- Constraint validation report
- Performance metrics
- University timetable in PDF and Excel formats

---

## Experimental Configuration

- Population Size: 30
- Maximum Iterations: 50
- Independent Runs: 40
- Optimization Algorithm: Adaptive TLBO
- Input Format: CSV
- Programming Language: Python 3.13

---

## Main Components

- Dataset Loader
- Timetable Generator
- Teacher Phase
- Learner Phase
- Adaptive Parameter Control
- Dynamic Priority Evaluation
- Faculty Satisfaction Evaluation
- Fitness Evaluation
- Elite Preservation
- Local Search
- Constraint Validation

---

## Results

The proposed Adaptive TLBO framework successfully:

- Generates conflict-free academic timetables
- Improves faculty satisfaction
- Optimizes classroom utilization
- Produces stable convergence behaviour
- Achieves higher fitness values than the baseline TLBO variants

---

## Citation

If you use this repository in academic work, please cite the corresponding conference paper.

---
