CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -O2 -D_GNU_SOURCE
TARGET = policyexec

.PHONY: all clean test

all: $(TARGET)

$(TARGET): policyexec.c
	$(CC) $(CFLAGS) -o $@ $<

POLICY ?= $(abspath $(CURDIR)/../../../config/policy.default.json)

test: $(TARGET)
	@echo "== list =="
	./$(TARGET) --policy $(POLICY) list
	@echo "== deny opencode =="
	./$(TARGET) --policy $(POLICY) check-tool opencode; test $$? -eq 1
	@echo "== allow read_file =="
	./$(TARGET) --policy $(POLICY) check-tool read_file; test $$? -eq 0
	@echo "== block mount =="
	./$(TARGET) --policy $(POLICY) check-command mount; test $$? -eq 1
	@echo "== allow echo =="
	./$(TARGET) --policy $(POLICY) check-command /bin/echo; test $$? -eq 0
	@echo "== red-team deny shell =="
	./$(TARGET) --policy $(POLICY) --role red-team check-tool shell; test $$? -eq 1
	@echo "== red-team allow read_file =="
	./$(TARGET) --policy $(POLICY) --role red-team check-tool read_file; test $$? -eq 0
	@echo "== ops allow shell =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool shell; test $$? -eq 0
	@echo "== ops allow delegate =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool delegate; test $$? -eq 0
	@echo "== ops allow memory_note =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool memory_note; test $$? -eq 0
	@echo "== ops deny opencode =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool opencode; test $$? -eq 1
	@echo "== ops deny vault_approve (HITL human-only) =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool vault_approve; test $$? -eq 1
	@echo "== ops deny unlisted vault_sync (allowlist fail-closed) =="
	./$(TARGET) --policy $(POLICY) --role ops check-tool vault_sync; test $$? -eq 1
	@echo "== blocklist crontab (H-005 expansion) =="
	./$(TARGET) --policy $(POLICY) check-command crontab; test $$? -eq 1
	@echo "== blocklist modprobe (H-005 expansion) =="
	./$(TARGET) --policy $(POLICY) check-command modprobe; test $$? -eq 1
	@echo "policyexec tests OK"

clean:
	rm -f $(TARGET)
