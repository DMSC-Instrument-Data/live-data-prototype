import mantid.simpleapi as mantid
from mantid.api import WorkspaceFactory
from mantid.api import AnalysisDataService
from mantid.api import StorageMode
from mantid.kernel import DateAndTime

from checkpoint import DataCheckpoint
from mantid_workspace_checkpoint import MantidWorkspaceCheckpoint
from mantid_workspace_transition import MantidWorkspaceTransition


class CreateMantidWorkspaceFromEventsTransition(MantidWorkspaceTransition):
    def __init__(self):
        super(CreateMantidWorkspaceFromEventsTransition, self).__init__(parents=[])

    def process(self, event_data, pulse_time):
        update = DataCheckpoint()
        update._data = (event_data, pulse_time)
        self.trigger_update({'no-parent':update})

    def _do_transition(self, data):
        event_data, pulse_time = data[0].data
        ws = WorkspaceFactory.Instance().create("EventWorkspace", 1, 1, 1);
        AnalysisDataService.Instance().addOrReplace('POWDIFF_test', ws)
        ws =  AnalysisDataService['POWDIFF_test']
        mantid.LoadInstrument(Workspace=ws, Filename='/home/simon/data/fake_powder_diffraction_data/POWDIFF_Definition.xml')
        ws.padSpectra()
        ws.getAxis(0).setUnit('tof')
        ws.setStorageMode(StorageMode.Distributed)
        for i in event_data:
            ws.getEventList(int(i[0])).addEventQuickly(float(i[1]), DateAndTime(pulse_time))
        return ws
