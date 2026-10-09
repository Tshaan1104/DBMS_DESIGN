# Framework for Database Design

## Assignment 1

**Prof. Ananthanarayana V.S.**\
Department of Information Technology\
N.I.T.K., Surathkal

## 1. Topic Selection

-   Select a topic involving **I/O-bound jobs**.

## 2. Problem Description

-   Describe the data flow and control flow.
-   Focus and clearly define the problem.
-   Identify relevant queries.
-   Specify realistic constraints.
-   State the number of sites/locations.

## 3. Logical Design

-   Construct relations using an **EER diagram**.

## 4. Advanced Logical Design

-   Apply normalization techniques up to **Third Normal Form (3NF)**.
-   Address fragmentation and data allocation.

## 5. Physical Design

### 5.1 Assumptions

-   Estimate the maximum number of tuples per relation.
-   Specify disk parameters, such as:
    -   Average seek time
    -   Average latency time
    -   IBG
    -   Block transfer time
    -   Block pointer size
    -   Other relevant parameters

### 5.2 Storage Requirements

-   Specify whether records are **spanned or unspanned**.

### 5.3 Access Methods

-   Consider:
    -   Ordered blocks
    -   Primary, clustering, and secondary indexes
    -   Multilevel indexes
    -   B-trees and B+ trees
-   Compare access methods in terms of:
    -   Number of blocks
    -   Additional space per record
    -   Number of disk accesses
-   Justify the selected access method.

### 5.4 Timings

-   Estimate the time required to access a record/table.
-   Consider buffering.
-   Estimate the time required to execute each query.

### 5.5 Work Area Space (WAS)

-   Estimate the maximum buffer space required for any computation.

### 5.6 System Specification

-   Estimate:
    -   Total disk space required
    -   Total memory space required (for the work area and buffers used
        to facilitate disk access)
    -   Response time for each query, including disk-access time and
        computation time

## 6. Submission

-   Submit the assignment by the end of the semester for evaluation.
