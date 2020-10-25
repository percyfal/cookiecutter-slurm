#!/usr/bin/env python3
import pytest
import time


@pytest.fixture
def profile(cookie_factory, data):
    cookie_factory()


@pytest.mark.slow
def test_no_timeout(smk_runner, profile):
    """Test that rule that updates runtime doesn't timeout"""
    smk_runner.make_target("timeout.txt")
    assert "Trying to restart" in smk_runner.output
    smk_runner.wait_for_status("COMPLETED")
    assert "Finished job" in smk_runner.output


@pytest.mark.slow
def test_timeout(smk_runner, profile):
    """Test that rule excessive runtime resources times out"""
    opts = (
        f'--cluster "sbatch --parsable -p {smk_runner.partition} {pytest.account} '
        '-c 1 -t {resources.runtime}" --attempt 1'
    )
    smk_runner.make_target("timeout.txt", options=opts, profile=None, asynchronous=True)
    # Discount queueing time
    smk_runner.wait_for_status("RUNNING")
    smk_runner.wait_while_status("RUNNING", tdelta=20, timeout=90)
    assert smk_runner.check_jobstatus("TIMEOUT|NODE_FAIL")


def test_profile_status_running(smk_runner, profile):
    """Test that slurm-status.py catches RUNNING status"""
    opts = (
        f'--cluster "sbatch --parsable -p {smk_runner.partition}'
        f' {pytest.account} -c 1 -t 1"'
    )
    smk_runner.make_target(
        "timeout.txt", options=opts, profile=None, asynchronous=True
    )  # noqa: E501
    smk_runner.wait_for_status("RUNNING", tdelta=5)
    jid = smk_runner.external_jobid[0]
    _, output = smk_runner.exec_run(
        cmd=f"{smk_runner.slurm_status} {jid}", stream=False
    )
    assert output.decode().strip() == "running"
    smk_runner.cancel_slurm_job(jid)


@pytest.mark.timeout(60)
def test_slurm_submit(smk_runner, profile):
    """Test that slurm-submit.py works"""
    jobscript = smk_runner.script("jobscript.sh")
    jobscript.write(
        (
            "#!/bin/bash\n"
            '# properties = {"cluster": {"job-name": "sm-job"},'
            '"input": [], "output": [], "wildcards": {}, "params": {},'
            '"rule": "slurm_submit"}\n'
        )
    )
    _, output = smk_runner.exec_run(
        cmd=f"{smk_runner.slurm_submit} {jobscript}", stream=False
    )
    jobid = int(output.decode().strip())
    time.sleep(5)
    assert smk_runner.check_jobstatus(
        "sm-job", options="--format=jobname", jobid=jobid)
    smk_runner.cancel_slurm_job(jobid)


@pytest.mark.timeout(60)
def test_group_job(smk_runner, profile):
    """Test that group job properties formatted as expected"""
    smk_runner.make_target("group_job.2.txt", stream=False)
    smk_runner.wait_for_status("COMPLETED", tdelta=5)
    assert "Submitted group job" in smk_runner.output
    assert "2 of 2 steps" in smk_runner.output


@pytest.mark.timeout(60)
def test_wildcard_job(smk_runner, profile):
    """Test that wildcard job properties formatted as expected"""
    smk_runner.make_target("wildcard.wc.txt")
    assert "Finished job" in smk_runner.output
