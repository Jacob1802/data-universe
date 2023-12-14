import os
from typing import List
from apify_client import ApifyClientAsync
from pydantic import BaseModel, Field, PositiveInt
import bittensor as bt

from dotenv import load_dotenv

from common.data import StrictBaseModel

load_dotenv()


class RunConfig(StrictBaseModel):
    """Configuration parameters for a single Apify Actor run."""

    api_key: str = Field(
        description="The Apify API token.",
        default=os.getenv("APIFY_API_TOKEN"),
        min_length=1,  # Can't be empty.
    )

    actor_id: str = Field(
        description="The ID of the actor to run.",
        min_length=1,  # Can't be empty.
    )

    timeout_secs: PositiveInt = Field(
        description="The timeout for the actor run.",
        default=60,
    )

    max_data_entities: PositiveInt = Field(
        description="The maximum number of items to be returned by the actor. The client will not be charged for more items than this value.",
        default=100,
    )

    debug_info: str = Field(
        description="Optional debug info to include in logs relating to this run."
    )


class ActorRunError(Exception):
    """Exception raised when an actor run fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ActorRunner:
    def __init__(self):
        pass

    async def run(config: RunConfig, run_input: dict) -> List[dict]:
        """
        Run an Apify actor and return the json results.

        Args:
            config (ActorConfig): The configuration to use for running the actor.
            run_input (dict): The input parameters for the actor run.

        Raises:
            ActorRunError: If the actor run fails, raises an exception, with the run details in the exception message.

        Returns:
            list[dict]: List of items fetched from the dataset.
        """

        client = ApifyClientAsync(config.api_key)

        bt.logging.trace(f"Running actor ({config.actor_id}) [{config.debug_info}]")
        run = await client.actor(config.actor_id).call(
            run_input=run_input,
            max_items=config.max_data_entities,
            timeout_secs=config.timeout_secs,
            # If not set, the client will wait indefinitely for the run to finish. Ensure we don't wait forever.
            wait_secs=config.timeout_secs + 5,
        )

        if "status" not in run or run["status"].casefold() != "SUCCEEDED".casefold():
            raise ActorRunError(
                f"Actor ({config.actor_id}) [{config.debug_info}] failed: {run}"
            )

        iterator = client.dataset(run["defaultDatasetId"]).iterate_items()

        items = [i async for i in iterator]

        bt.logging.trace(
            f"Actor ({config.actor_id}) [{config.debug_info}] returned {len(items)} items"
        )
        return items
