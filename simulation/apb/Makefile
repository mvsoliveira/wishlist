SIM            ?= verilator
DESIGN         ?= signalprocessor

PWD     := $(shell pwd)
FIRMWARE := $(PWD)/../../examples/firmware

export PYTHONPATH := $(PWD)/../../:$(PYTHONPATH)

COMPILE_ARGS += -I$(FIRMWARE)
COMPILE_ARGS += --timing -DCOCOTB_SIM=1
COMPILE_ARGS += -Wno-EOFNEWLINE
COMPILE_ARGS += -Wno-IMPORTSTAR
COMPILE_ARGS += -Wno-WIDTHEXPAND
COMPILE_ARGS += --public-flat-rw

# pkg.sv must come first so package types are defined before use
VERILOG_SOURCES  = $(FIRMWARE)/$(DESIGN)_pkg.sv
VERILOG_SOURCES += $(FIRMWARE)/$(DESIGN)_address_decoder_apb.sv

export BACKANNOTATED_YAML := $(FIRMWARE)/$(DESIGN)_backannotated.yaml

TOPLEVEL := $(DESIGN)_address_decoder_apb
MODULE   := edawishlist.apb_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim
