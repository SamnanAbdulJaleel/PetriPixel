import math
import pygame
from pygame.sprite import Sprite
import helper
from handlers.genetics import Genome, Phenome
import numpy as np
import random
import noise
from enums import Base
from uuid import uuid4


class Creature(Sprite):
    def __init__(self, surface, context):
        self.id = uuid4()
        super().__init__()

        position = context.get("position", None)
        parents = context.get("parents", None)
        initial_energy = context.get("initial_energy", None)

        color = context.get("color", (124, 245, 255))
        # self.phenome = Phenome(context.get("phenome"))  # Uncomment if needed
        self.color = color
        self.radius = context.get("radius", 5)
        self.mating_timeout = random.randint(150, 300)
        self.genome = Genome(
            context.get("genome")
        )  # Assuming Genome is defined elsewhere
        self.max_energy = 500
        self.speed = 1

        # Keeping deep dictionaries
        self.colors = {
            "alive": color,
            "dead": (0, 0, 0),
            "reproducing": (255, 255, 255),
        }

        self.border = {
            "color": (100, 57, 255),
            "thickness": 2.5,
        }

        self.vision = {
            "radius": 40,
            "color": {
                Base.found: (0, 255, 0, 25),
                Base.looking: (0, 255, 255, 25),
            },
            "food": {"state": Base.looking, "rect": None},
            "mate": {"state": Base.looking, "mate": None},
        }

        color = "#f94144"

        self.angle = 0  # degrees
        self.hunger = 2
        self.alive = True
        self.time = 0
        self.time_alive = 0
        self.acceleration_factor = 0.1
        self.td = random.randint(0, 1000)  # for pnoise generation
        self.energy = initial_energy if initial_energy else self.max_energy

        # Grouped states in a dictionary
        self.mating = {
            "state": Base.not_ready,
            "mate": None,
            "timeout": self.mating_timeout,
        }

        self.env_surface = surface
        self.noise = noise

        self.parents = parents

        self.done = False
        self.color = self.color

        # Create a transparent surface for the creature
        # +4 for radius
        surface_size = (
            (2 * self.radius) + self.border["thickness"] + (2 * self.vision["radius"])
        )
        self.image = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)

        # Calculate center of the surface
        self.center = (surface_size // 2, surface_size // 2)

        # Get rect for positioning
        self.rect = self.image.get_rect()
        self.rect.center = position or helper.get_random_position(surface)

    def draw(self, surface, vision_circle=False):
        if not self.alive:
            return

        # radius = self.radius
        # border_thickness = self.border["thickness"]
        # total_radius = radius + border_thickness
        # center = (total_radius, total_radius)

        # self.surface = pygame.Surface(
        #     (total_radius * 2, total_radius * 2), pygame.SRCALPHA
        # )

        if vision_circle:
            # Vision circle
            pygame.draw.circle(
                self.image,
                self.vision["color"][self.vision["food"]["state"]],
                self.center,
                self.radius + self.vision["radius"],
            )

        color = (0, 0, 0)
        if not self.alive:
            color = (0, 0, 0)
        elif self.mating["state"] == Base.mating:
            color = (255, 255, 255)
        elif self.mating["state"] == Base.ready:
            color = (0, 0, 255)

        # Border
        pygame.draw.circle(
            self.image,
            color,
            self.center,
            self.radius + self.border["thickness"],
        )

        color = self.color
        if not self.alive:
            color = (0, 0, 0)

        # Creature
        pygame.draw.circle(
            self.image,
            color,
            self.center,
            self.radius,
        )

        surface.blit(self.image, self.rect.topleft)

    def step(self):
        self.time += 1

        if not self.done:
            self.energy -= 1

            if self.energy <= 0:
                self.die()
                return

            obs = self.genome.observe(self)
            outputs = self.genome.forward(obs)
            self.genome.step(outputs, self)
            return
            self.time_alive += 1
            self.mating["timeout"] -= 1

            if self.mating["timeout"] <= 0:
                if (self.energy >= 50) and (self.mating["state"] != Base.mating):
                    self.mating["state"] = Base.ready
                    # if random.random() < 0.6:
                    #     pass

            self.update_vision_state()
            self.angle = self.update_angle()

        if not self.alive:
            if (self.time - self.time_alive) < 100:
                return

    def set_mate(self, mate):
        self.mating["state"] = Base.mating
        self.mating["mate"] = mate

    def remove_mate(self):
        self.mating["state"] = Base.not_ready
        self.mating["mate"] = None
        self.mating["timeout"] = self.mating_timeout

    def update_vision_state(self):
        if rect := self.rect.collideobjects(
            [food.rect for food in self.env.plant_manager.get_plants()],
            key=lambda rect: rect,
        ):
            self.vision["food"]["state"] = Base.found
            self.vision["food"]["rect"] = rect
        else:
            self.vision["food"]["state"] = Base.looking
            self.vision["food"]["rect"] = None

        other_creatures = [
            creature
            for creature in self.env.creatures
            if creature is not self
            and creature.mating["state"] == Base.ready
            and creature.alive
        ]

        if creature_index := self.rect.collidelistall(
            [creature.rect for creature in other_creatures]
        ):
            self.vision["mate"]["state"] = Base.found
            self.vision["mate"]["mate"] = other_creatures[creature_index[0]]

        else:
            self.vision["mate"]["state"] = Base.looking
            self.vision["mate"]["mate"] = None
        return

    def update_angle(self):
        angle = noise.snoise2(self.td, 0) * 360
        self.td += 0.01
        return angle

    def reset(self):
        self.hunger = 2
        self.done = False
        self.energy = self.max_energy
        self.closest_edge = None
        self.original_position = helper.get_random_position(self.env_window)
        self.rect.center = self.original_position

    def progress(self):
        if not self.done:
            if self.hunger == 0:
                self.reproduce()
            elif self.hunger == 1:
                pass
            else:
                self.die()
            self.done = True

    def reproduce(self):
        self.env.children.add(
            Creature(
                self.env,
                self.env_window,
                self.creature_manager,
                radius=self.radius,
            )
        )

    def die(self):
        self.alive = False
        self.done = True

    def eat(self):
        self.hunger -= 1
        self.energy += self.max_energy // 2
        self.env.remove_food(self.rect.center)

    def move_towards(self, target, speed=None):
        speed = speed or self.speed
        direction = np.array(target) - np.array(self.rect.center)
        distance_to_target = np.linalg.norm(direction)

        if distance_to_target <= speed:
            self.rect.center = target
        else:
            direction = direction / distance_to_target
            new_position = np.array(self.rect.center) + direction * speed
            self.rect.center = new_position

        # Normalize position to stay within env_window bounds
        self.rect = helper.normalize_position(self.rect, self.env_window)

    def move_in_direction(self, direction):
        direction = np.radians(direction)

        # Calculate the change in x and y coordinates
        dx = self.speed * np.cos(direction)
        dy = self.speed * np.sin(direction)

        # Update the current position
        new_position = (self.rect.center[0] + dx, self.rect.center[1] + dy)

        self.rect.center = new_position
        self.rect = helper.normalize_position(self.rect, self.env_window)

    def get_observation(self):
        if not hasattr(self, "parsed_dna"):
            self.parsed_dna = self.creature_manager.get_parsed_dna(self.DNA)

        observations = []
        # for sensor in self.parsed_dna:
        #     observation_func = getattr(SensorManager, f"obs_{sensor}", None)
        #     if observation_func is not None:
        #         observation = observation_func(self.env, self)
        #         observations.append(observation)
        #     else:
        #         # Handle the case where the sensor doesn't exist
        #         raise Exception(f"Error: No method for sensor {sensor}")
        return observations


class Plant(Sprite):
    def __init__(
        self,
        env_surface,
        pos=None,
        radius=4,
        n=200,
        color=(124, 176, 109),
    ):
        super().__init__()

        self.env_surface = env_surface

        self.radius = radius
        self.n = n

        # Create a transparent surface for the food
        self.image = pygame.Surface(((2 * radius), (2 * radius)), pygame.SRCALPHA)

        # Random position within env_window bounds
        self.position = pos or (
            random.randint(radius + 75, env_surface.get_width() - radius - 75),
            random.randint(radius + 75, env_surface.get_height() - radius - 75),
        )

        # Create the circle on the image surface (center of the surface)
        pygame.draw.circle(self.image, color, (radius, radius), radius)

        # Get rect for positioning
        self.rect = self.image.get_rect()
        self.rect.center = self.position

    def draw(self):
        # Blit the food image to the env_window at its position
        self.env_window.blit(self.image, self.rect.topleft)
