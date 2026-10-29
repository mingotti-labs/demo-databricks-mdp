"""Tests for cicd/run_dev.py: the parts that build names and payloads."""

from run_dev import find_job_id, job_name, run_payload


def test_job_name():
    assert job_name("yahoo") == "[dev svc_cicd_github] run--yahoo--dev"


def test_run_payload():
    assert run_payload(7, ["reload_symbols=AAPL,KO", "verify=true"]) == {
        "job_id": 7,
        "job_parameters": {"reload_symbols": "AAPL,KO", "verify": "true"},
    }
    assert run_payload(7, []) == {"job_id": 7, "job_parameters": {}}


def test_find_job_id_exact_name_only():
    jobs = [
        {"job_id": 1, "settings": {"name": "[dev handsonessential] run--yahoo--dev"}},
        {"job_id": 2, "settings": {"name": "[dev svc_cicd_github] run--yahoo--dev"}},
    ]
    assert find_job_id(jobs, job_name("yahoo")) == 2
    assert find_job_id(jobs, job_name("sec")) is None
