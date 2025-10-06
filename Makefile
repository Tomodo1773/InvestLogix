.PHONY: act-pytest

ACT_WORKFLOW := .github/workflows/pytest.yml
ACT_JOB := test
ACT_SECRETS := .secrets
ACT_DOCKER_HOST := unix:///var/run/docker.sock

act-pytest:
	gh act -W $(ACT_WORKFLOW) -j $(ACT_JOB) --secret-file $(ACT_SECRETS) --env DOCKER_HOST=$(ACT_DOCKER_HOST)
