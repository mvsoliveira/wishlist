SIM            ?= verilator
DESIGN         ?= signalprocessor

PWD     := $(shell pwd)
FIRMWARE := $(PWD)/../../firmware

export PYTHONPATH := $(PWD)/../../:$(PYTHONPATH)

COMPILE_ARGS += -Wall
COMPILE_ARGS += -Wno-EOFNEWLINE
COMPILE_ARGS += -Wno-IMPORTSTAR
COMPILE_ARGS += -Wno-WIDTHEXPAND
COMPILE_ARGS += --public-flat-rw

# signalprocessor_pkg.sv must come first so package types are defined before use
VERILOG_SOURCES  = $(FIRMWARE)/$(DESIGN)_pkg.sv
VERILOG_SOURCES += $(FIRMWARE)/$(DESIGN)_address_decoder.sv
VERILOG_SOURCES += $(FIRMWARE)/$(DESIGN)_instantiation.sv

export BACKANNOTATED_YAML := $(FIRMWARE)/$(DESIGN)_backannotated.yaml

TOPLEVEL := $(DESIGN)_instantiation
MODULE   := edawishlist.wishbone_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim
