import pygame
import random
import math
from scipy.spatial import ConvexHull

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 400
FPS = 60
SPEED = 6

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dino Game")

# Background
bg = pygame.image.load("../Sprites/bg_1.png").convert()
bg_width = bg.get_width()
tiles = math.ceil(SCREEN_WIDTH / bg_width) + 1
scroll = 0

broken_obstacle_images = [
    "../Sprites/broken_cacti_1.png",
    "../Sprites/broken_cacti_2.png",
    "../Sprites/broken_cacti_3.png"
]


def draw_background(screen):
    global scroll
    for i in range(0, tiles):
        screen.blit(bg, (i * bg_width + scroll, 0))
    scroll -= SPEED
    if abs(scroll) > bg_width:
        scroll = 0

def get_convex_hull(image):
    mask = pygame.mask.from_surface(image)
    points = mask.outline()
    if len(points) < 3:
        return []
    hull = ConvexHull(points)
    hull_points = [points[vertex] for vertex in hull.vertices]
    return hull_points

def draw_convex_hull(surface, points, color):
    if len(points) < 3:
        return
    pygame.draw.polygon(surface, color, points, 1)

class QuadTree:
    def __init__(self, x, y, width, height, max_objects=10, max_levels=5, level=0):
        self.bounds = pygame.Rect(x, y, width, height)
        self.max_objects = max_objects
        self.max_levels = max_levels
        self.level = level
        self.objects = []
        self.nodes = []

    def clear(self):
        self.objects = []
        for node in self.nodes:
            node.clear()
        self.nodes = []

    def split(self):
        sub_width = self.bounds.width // 2
        sub_height = self.bounds.height // 2
        x, y = self.bounds.topleft

        self.nodes = [
            QuadTree(x, y, sub_width, sub_height, self.max_objects, self.max_levels, self.level + 1),
            QuadTree(x + sub_width, y, sub_width, sub_height, self.max_objects, self.max_levels, self.level + 1),
            QuadTree(x, y + sub_height, sub_width, sub_height, self.max_objects, self.max_levels, self.level + 1),
            QuadTree(x + sub_width, y + sub_height, sub_width, sub_height, self.max_objects, self.max_levels, self.level + 1)
        ]

    def get_index(self, rect):
        indexes = []
        vertical_midpoint = self.bounds.x + self.bounds.width // 2
        horizontal_midpoint = self.bounds.y + self.bounds.height // 2

        top_quadrant = rect.top < horizontal_midpoint and rect.bottom < horizontal_midpoint
        bottom_quadrant = rect.top > horizontal_midpoint

        if rect.left < vertical_midpoint and rect.right < vertical_midpoint:
            if top_quadrant:
                indexes.append(0)
            if bottom_quadrant:
                indexes.append(2)
        elif rect.left > vertical_midpoint:
            if top_quadrant:
                indexes.append(1)
            if bottom_quadrant:
                indexes.append(3)

        return indexes

    def insert(self, obj):
        if self.nodes:
            indexes = self.get_index(obj.rect)
            for index in indexes:
                self.nodes[index].insert(obj)
            return

        self.objects.append(obj)

        if len(self.objects) > self.max_objects and self.level < self.max_levels:
            if not self.nodes:
                self.split()

            i = 0
            while i < len(self.objects):
                indexes = self.get_index(self.objects[i].rect)
                for index in indexes:
                    self.nodes[index].insert(self.objects[i])
                self.objects.pop(i)
            else:
                i += 1

    def retrieve(self, obj):
        indexes = self.get_index(obj.rect)
        objects = self.objects[:]
        if self.nodes:
            for index in indexes:
                objects.extend(self.nodes[index].retrieve(obj))
        return objects

class Player:
    def __init__(self, x, y):
        self.running_images = [
            pygame.image.load("../Sprites/run_1.png").convert_alpha(),
            pygame.image.load("../Sprites/run_2.png").convert_alpha()
        ]
        self.jumping_image = pygame.image.load("../Sprites/jump_1.png").convert_alpha()
        self.crouching_images = [
            pygame.image.load("../Sprites/crouch_1.png").convert_alpha(),
            pygame.image.load("../Sprites/crouch_2.png").convert_alpha()
        ]
        self.images = self.running_images
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.animation_time = 0.1
        self.last_update = pygame.time.get_ticks()
        self.is_jumping = False
        self.is_crouching = False
        self.jump_speed = -19
        self.gravity = 1
        self.velocity_y = 0
        self.ground = y
        self.crouch_height = self.rect.height // 2  # Height when crouching
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update > self.animation_time * 1000:
            self.last_update = current_time
            self.index = (self.index + 1) % len(self.images)
            if not self.is_jumping and not self.is_crouching:
                self.image = self.images[self.index]
                self.mask = pygame.mask.from_surface(self.image)

        if self.is_jumping:
            self.image = self.jumping_image
            self.velocity_y += self.gravity
            self.rect.y += self.velocity_y
            self.hull_points = get_convex_hull(self.image)
            self.mask = pygame.mask.from_surface(self.image)

            if self.rect.y >= self.ground:
                self.rect.y = self.ground
                self.is_jumping = False
                self.velocity_y = 0
                self.images = self.running_images
                self.image = self.images[self.index]
                self.hull_points = get_convex_hull(self.image)
                self.mask = pygame.mask.from_surface(self.image)

        elif self.is_crouching:
            self.images = self.crouching_images
            self.image = self.images[self.index]
            self.rect.height = self.crouch_height
            self.hull_points = get_convex_hull(self.image)
            self.mask = pygame.mask.from_surface(self.image)

        else:
            self.images = self.running_images
            self.rect.height = self.image.get_height()
            self.hull_points = get_convex_hull(self.image)
            self.mask = pygame.mask.from_surface(self.image)


    def jump(self):
        if not self.is_jumping and not self.is_crouching:
            self.is_jumping = True
            self.velocity_y = self.jump_speed

    def crouch(self, crouching):
        self.is_crouching = crouching
        if crouching:
            self.rect.height = self.crouch_height
            self.rect.y += self.crouch_height
        else:
            self.rect.height = self.image.get_height()
            self.rect.y -= self.crouch_height

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        draw_convex_hull(screen, [(p[0] + self.rect.x, p[1] + self.rect.y) for p in self.hull_points], (255, 0, 0))

    def check_collision(self, objects):
        for obj in objects:
            if pygame.sprite.collide_mask(self, obj):
                return True
        return False

class Obstacle:
    def __init__(self, x, y, image):
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.speed = 5
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect.x -= SPEED

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        draw_convex_hull(screen, [(p[0] + self.rect.x, p[1] + self.rect.y) for p in self.hull_points], (0, 255, 0))

    def is_off_screen(self):
        return self.rect.right < 0

class BrokenObstacle:
    def __init__(self, x, y, image_path):
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def update(self):
        self.rect.x -= SPEED

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def is_off_screen(self):
        return self.rect.right < 0

class Meteor:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.speed = random.randint(5, 15)
        self.image = pygame.transform.scale(meteor_image, (self.size, self.size))
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.y += self.speed
        self.rect.topleft = (self.x, self.y)
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

        if self.y >= SCREEN_HEIGHT - 183:
            self.y = SCREEN_HEIGHT - 183
            return True

        return False

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        draw_convex_hull(screen, [(p[0] + self.rect.x, p[1] + self.rect.y) for p in self.hull_points], (0, 0, 255))

    def is_off_screen(self):
        return self.y > SCREEN_HEIGHT

    def check_collision(self, obj):
        return pygame.sprite.collide_mask(self, obj)

class Bird:
    def __init__(self, x, y):
        self.images = [
            pygame.image.load("../Sprites/bird1.png").convert_alpha(),
            pygame.image.load("../Sprites/bird2.png").convert_alpha()
        ]
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.animation_time = 0.1
        self.last_update = pygame.time.get_ticks()
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update > self.animation_time * 1000:
            self.last_update = current_time
            self.index = (self.index + 1) % len(self.images)
            self.image = self.images[self.index]
            self.mask = pygame.mask.from_surface(self.image)
        self.rect.x -= SPEED

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        draw_convex_hull(screen, [(p[0] + self.rect.x, p[1] + self.rect.y) for p in self.hull_points], (0, 255, 0))

    def is_off_screen(self):
        return self.rect.right < 0

class BrokenBird:
    def __init__(self, x, y):
        self.image = pygame.image.load("../Sprites/broken_bird.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def update(self):
        self.rect.x -= SPEED
        self.rect.y += 5

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def is_off_screen(self):
        return self.rect.right < 0

class Crater:
    def __init__(self, x, y, size):
        self.original_image = pygame.image.load("../Sprites/krater.png").convert_alpha()
        self.image = pygame.transform.scale(self.original_image, (size, size))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y - size // 2)  # Adjust y to center the crater
        self.hull_points = get_convex_hull(self.image)
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        draw_convex_hull(screen, [(p[0] + self.rect.x, p[1] + self.rect.y) for p in self.hull_points], (0, 0, 255))

    def update(self):
        self.rect.x -= SPEED

    def is_off_screen(self):
        return self.rect.right < 0

# Load images and sounds
obstacle_images = [
    pygame.image.load("../Sprites/cactus1.png").convert_alpha(),
    pygame.image.load("../Sprites/cactus2.png").convert_alpha(),
    pygame.image.load("../Sprites/cactus3.png").convert_alpha()
]
meteor_image = pygame.image.load("../Sprites/meteor.png").convert_alpha()

# Initialize game elements
player = Player(100, SCREEN_HEIGHT - 210)
meteors = []
meteor_timer = 0
meteor_interval = 3000  # 3 seconds

obstacles = []
obstacle_timer = 0
obstacle_interval = 1350

birds = []
bird_timer = 0
bird_interval = 2000  # 2 seconds

quadtree = QuadTree(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

# Initialize score and game speed
points = 0
game_speed = 5
font = pygame.font.Font('freesansbold.ttf', 30)


def score():
    global points, game_speed
    points += 1
    if points % 100 == 0:
        game_speed += 1

    text = font.render("Score: " + str(points), True, (0, 0, 0))
    textRect = text.get_rect()
    textRect.center = (800, 50)
    screen.blit(text, textRect)


clock = pygame.time.Clock()


def game_over_screen():
    global points
    screen.fill((255, 255, 255))
    font = pygame.font.Font('freesansbold.ttf', 30)
    score_text = font.render("Your Score: " + str(points), True, (0, 0, 0))
    text = font.render("Press any Key to play again", True, (0, 0, 0))

    text_rect = text.get_rect()
    text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    score_rect = score_text.get_rect()
    score_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)

    screen.blit(text, text_rect)
    screen.blit(score_text, score_rect)
    pygame.display.update()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                waiting = False


# Game loop
run = True
game_active = True
broken_obstacles = []
broken_birds = []
craters = []

while run:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if game_active:
                if event.key == pygame.K_UP:
                    player.jump()
                if event.key == pygame.K_DOWN:
                    player.crouch(True)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_DOWN:
                player.crouch(False)

    if game_active:
        SPEED += 0.0025
        screen.fill((0, 0, 0))
        draw_background(screen)
        player.update()
        player.draw(screen)

        # Clear and rebuild the quadtree
        quadtree.clear()
        quadtree.insert(player)
        for obstacle in obstacles:
            quadtree.insert(obstacle)
        for bird in birds:
            quadtree.insert(bird)
        for meteor in meteors:
            quadtree.insert(meteor)
        for crater in craters:
            quadtree.insert(crater)

        current_time = pygame.time.get_ticks()
        if current_time - obstacle_timer > obstacle_interval:
            obstacle_timer = current_time
            if random.choice([True, True, True, False]):
                # Generate cactus
                obstacle_index = random.randrange(len(obstacle_images))
                obstacle_image = obstacle_images[obstacle_index]
                obstacle_y = SCREEN_HEIGHT - obstacle_image.get_height() - 135
                obstacle = Obstacle(SCREEN_WIDTH, obstacle_y, obstacle_image)
                obstacles.append(obstacle)
            else:
                # Generate bird
                bird_y = random.choice([SCREEN_HEIGHT - 230, SCREEN_HEIGHT - 250, SCREEN_HEIGHT - 290])
                bird = Bird(SCREEN_WIDTH, bird_y)
                birds.append(bird)

        if current_time - meteor_timer > meteor_interval:
            meteor_timer = current_time
            #meteor_x = 200
            meteor_x = random.randint(200, SCREEN_WIDTH - 50)
            meteor_y = -20
            meteor_size = random.randint(50, 100)
            meteor = Meteor(meteor_x, meteor_y, meteor_size)
            meteors.append(meteor)

        for obstacle in obstacles:
            obstacle.update()
            obstacle.draw(screen)

        meteors_to_remove = []
        for meteor in meteors:
            if meteor.update():
                meteors_to_remove.append(meteor)
                craters.append(Crater(meteor.rect.x, SCREEN_HEIGHT - 133, meteor.size))
            else:
                meteor.draw(screen)

            for obstacle in obstacles:
                if pygame.sprite.collide_mask(meteor, obstacle):
                    broken_obstacle_image = broken_obstacle_images[obstacle_index]
                    broken_obstacle = BrokenObstacle(obstacle.rect.x, obstacle.rect.y+25, broken_obstacle_image)
                    broken_obstacles.append(broken_obstacle)
                    meteors.remove(meteor)
                    obstacles.remove(obstacle)
                    break

            for bird in birds:
                if pygame.sprite.collide_mask(meteor, bird):
                    broken_bird = BrokenBird(bird.rect.x, bird.rect.y)
                    broken_birds.append(broken_bird)
                    meteors.remove(meteor)
                    birds.remove(bird)
                    break

        for crater in craters:
            crater.update()
            crater.draw(screen)

        for bird in birds:
            bird.update()
            bird.draw(screen)

        for broken_obstacle in broken_obstacles:
            broken_obstacle.update()
            broken_obstacle.draw(screen)

        for broken_bird in broken_birds:
            broken_bird.update()
            broken_bird.draw(screen)

        broken_obstacles = [broken_obstacle for broken_obstacle in broken_obstacles if not broken_obstacle.is_off_screen()]
        broken_birds = [broken_bird for broken_bird in broken_birds if not broken_bird.is_off_screen()]
        obstacles = [obstacle for obstacle in obstacles if not obstacle.is_off_screen()]
        meteors = [meteor for meteor in meteors if not meteor.is_off_screen()]
        birds = [bird for bird in birds if not bird.is_off_screen()]
        craters = [crater for crater in craters if not crater.is_off_screen()]

        for meteor in meteors_to_remove:
            meteors.remove(meteor)

        score()

        potential_collisions = quadtree.retrieve(player)
        if player.check_collision([obj for obj in potential_collisions if isinstance(obj, (Obstacle, Bird, Meteor, Crater))]):
            game_active = False

    else:
        game_over_screen()
        points = 0
        obstacles.clear()
        birds.clear()
        meteors.clear()
        broken_obstacles.clear()
        broken_birds.clear()
        craters.clear()
        player = Player(100, SCREEN_HEIGHT - 210)
        SPEED = 6
        game_active = True

    pygame.display.update()

pygame.quit()