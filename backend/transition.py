import weakref

from checkpoint import Checkpoint
from checkpoint import DataCheckpoint
from checkpoint import CompositeCheckpoint


class Transition(object):
    def __init__(self, input_checkpoint = None):
        # TODO merge inputs into CompositeCheckpoint? No! They may have nothing to do with each other
        # We keep a *weakref* to upstream checkpoints to break cyclic references.
        self._input_checkpoint = weakref.ref(input_checkpoint)
        # TODO move such an init to child classes? i.e., child defines what outputs it has!
        # no.. just replace this later by appropriate CompositeCheckpoint
        # TODO would it make sense to init this as Checkpoint() instead?
        self._checkpoint = DataCheckpoint()

    def get_checkpoint(self):
        return self._checkpoint

    # TODO cover case of adding transition after first data arrives

    def trigger_update(self):
        can_update = self._can_do_updates()
        self._trigger(can_update)

    def trigger_rerun(self):
        can_update = False
        self._trigger(can_update)

    def _trigger(self, can_update):
        # Temporarily get the normal ref to avoid messe code in various functions.
        input_checkpoint = self._input_checkpoint()
        # TODO for now we are covering only single-input transitions
        self._checkpoint = self._make_composite_if_necessary(input_checkpoint, self._checkpoint)
        self._recurse_trigger(can_update, input_checkpoint, self._checkpoint)

    def _make_composite_if_necessary(self, checkpoint_in, checkpoint_out):
        if isinstance(checkpoint_in, CompositeCheckpoint):
            if not isinstance(checkpoint_out, CompositeCheckpoint):
                return CompositeCheckpoint(len(checkpoint_in))
            elif len(checkpoint_in) != len(checkpoint_out):
                return CompositeCheckpoint(len(checkpoint_in))
        return checkpoint_out

    def _recurse_trigger(self, can_update, checkpoint_in, checkpoint_out):
        if isinstance(checkpoint_in, CompositeCheckpoint):
            for i in range(len(checkpoint_in)):
                checkpoint_out[i] = self._make_composite_if_necessary(checkpoint_in[i], checkpoint_out[i])
                self._recurse_trigger(can_update, checkpoint_in[i], checkpoint_out[i])
        else:
            self._do_trigger(can_update, checkpoint_in, checkpoint_out)

    def _do_trigger(self, can_update, checkpoint_in, checkpoint_out):
        data, diff = checkpoint_in.get_data()
        if can_update and (diff is not None):
            result = self._do_transition(diff)
            checkpoint_out.append(result)
        else:
            result = self._do_transition(data)
            checkpoint_out.replace(result)

    #def trigger(self):
    #    is_update, inputs = self._collect_inputs()
    #    # build list of actual input data, depending on whether transition can work on updates or not
    #    # TODO what about nesting!?
    #    outputs = [ self._do_transition(item) for item in inputs ]
    #    outputs = self._do_transition(inputs)

    #    if is_update:
    #        # TODO make sure this loop is *not* over CompositeCheckpoint!
    #        # output should always be a single composite checkpoint
    #        for i, output in enumerate(outputs):
    #            self._checkpoints[i].append(output)
    #    else:
    #        for i, output in enumerate(outputs):
    #            self._checkpoints[i].replace(output)

    #def _collect_inputs(self):
    #    inputs = [ checkpoint.get_data() for checkpoint in self._input_checkpoints ]
    #    is_update = self._is_update(inputs) and self._can_do_updates()
    #    inputs_base = [ item[0] for item in inputs ]
    #    inputs_diff = [ item[1] for item in inputs ]
    #    for i,item in enumerate(inputs_diff):
    #        if item is not None:
    #            inputs_base[i] = item
    #    return is_update, inputs_base

    #def _is_update(self, inputs):
    #    updates = [ data[1] for data in inputs ]
    #    update_count = len(updates) - updates.count(None)
    #    if update_count == 0:
    #        return False
    #    if update_count == 1:
    #        return True
    #    raise RuntimeError('Found {} updated inputs, but only one update at a time is supported.'.format(update_count))

    def _do_transition(self, data):
        raise RuntimeError('Transition._do_transition() must be implemented in child classes!')

    def _can_do_updates(self):
        """Can this transition work on data updates, i.e., partial data?
        Reimplement this in child classes to change the default (True)"""
        return True


class IdentityTransition(Transition):
    def __init__(self, input_checkpoint = None):
        super(IdentityTransition, self).__init__(input_checkpoint)

    def _do_transition(self, data):
        return data


class UpperCaseTransition(Transition):
    def __init__(self, input_checkpoint = None):
        super(UpperCaseTransition, self).__init__(input_checkpoint)

    def _do_transition(self, data):
        return data.upper()
